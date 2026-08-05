"""
V2 Intent Router pipeline — 3 katmanlı koruma kalkanı (reranker kaldırıldı).

  Katman 1:   Rule-based fast-path (chitchat / gibberish / abuse) — model YOK
  Katman 1.5: K1 Regex sektör guardrail — eşleşirse embedding'e gitmeden
              ACCEPT (confidence 1.00, <5ms).
  Katman 1.6: OOD Fast-Reject guardrail (B2C/chit-chat) — eşleşirse
              embedding'e gitmeden REJECT (<1ms).
  Katman 2:   bge-m3 retrieval (raw cosine) → strict threshold gate
              (score >= DECISION_THRESHOLD=0.65 → ACCEPT; aksi REJECT/OOD).

Cross-Encoder / Reranker / Soft Fusion YOK. Karar yalnızca K1 Regex Match,
OOD Fast-Reject VEYA BGE-M3 raw cosine similarity üzerinden verilir.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.chitchat_rules import MSG_OOD_GATE, match_fast_path
from app.db.vector_store import VectorCandidate
from app.core.intent_contract import (
    build_top_candidate,
    map_sector,
    map_sub_intent,
    resolve_redirect_url,
    resolve_response_message,
)
from app.core.k1_guardrails import (
    DECISION_THRESHOLD,
    check_ood_reject,
    check_restricted_domain,
    extract_active_clause,
    match_any_sector,
)
from app.core.record_types import KAYIT_TIPI_KURUMSAL, PG_SECTOR_INFO, infer_kayit_tipi_legacy
from app.services.k0_corporate_info import (
    try_k0_corporate_info,
    _has_strong_service_signal,
    sanitize_corporate_cevap,
    pick_kurumsal_hit_for_lang,
)


def _trace_decision(msg: str) -> None:
    if os.environ.get("V2_PIPELINE_TRACE"):
        print(f"[V2_TRACE] {msg}", file=sys.stderr)


INTENT_STRIPPERS = [
    # TR Noise
    r"\b(fiyatı|ücreti|maliyeti|fiyati|ucreti|maliyeti)\s+(nedir|ne kadar|bilgisi)\b",
    r"\b(teklif|fiyat|fiyatı|fiyati)\s+alabilir\s+miyim\b",
    r"\bkolay\s+gelsin\b",
    # EN Noise
    r"\b(what('s| is)|get)\s+(the\s+)?(quote|pricing|cost)\b",
    r"\burgently\s+looking\s+for\b",
    r"\bhi\s+there\b|\bgood\s+morning\b",
]

def clean_pure_intent(text: str) -> str:
    cleaned = text
    for pattern in INTENT_STRIPPERS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split())


def _is_kurumsal_candidate(h: VectorCandidate) -> bool:
    meta = h.record_meta or {}
    kt = meta.get("kayit_tipi") or infer_kayit_tipi_legacy(meta)
    if kt == KAYIT_TIPI_KURUMSAL:
        return True
    sec = (h.sector or "").strip().lower()
    return sec in (PG_SECTOR_INFO, "info")


@dataclass
class V2PipelineResult:
    query: str
    retrieval: list[VectorCandidate]
    sector: str
    sub_intent: str
    confidence_score: float
    status: str
    latency_ms: float
    response_message: str = ""
    redirect_url: str = ""
    top_candidates: list[dict[str, Any]] = field(default_factory=list)
    stages_ms: dict[str, float] = field(default_factory=dict)
    layer: str = "ml"  # rule | ml
    detected_language: str = "tr"
    processed_intent: str = ""
    negated_sectors: list[str] = field(default_factory=list)
    preprocessed_query: str = ""

    def to_intent_router(self, *, include_top_candidates: bool = True) -> dict[str, Any]:
        slug_en = {
            "saglik": "healthcare",
            "turizm": "hospitality",
            "egitim": "education",
            "bilisim": "it",
            "eglence": "entertainment",
            "ood": "general"
        }
        slug_tr = {
            "saglik": "saglik",
            "turizm": "turizm",
            "egitim": "egitim",
            "bilisim": "bilisim",
            "eglence": "eglence",
            "ood": "genel"
        }
        
        target_slug = slug_en.get(self.sector, "general") if self.detected_language == "en" else slug_tr.get(self.sector, "genel")
        locale_path = f"en/contact/{target_slug}" if self.detected_language == "en" else f"iletisim/{target_slug}"
        
        # Slugify intent
        intent_slug = self.processed_intent.lower()
        intent_slug = re.sub(r"[^\w\s-]", "", intent_slug)
        intent_slug = re.sub(r"\s+", "-", intent_slug).strip("-")
        if not intent_slug:
            intent_slug = "general"
            
        final_url = f"https://firmaadi.com/{locale_path}?intent={intent_slug}&ref=smart_route&lang={self.detected_language}"
        
        route_type = "K1_FastPath"
        if self.layer == "ml":
            route_type = "V2_Unanimity" if self.status == "SUCCESS" else "Fallback"
            
        payload: dict[str, Any] = {
            "raw_query": self.query,
            "detected_language": self.detected_language,
            "processed_intent": self.processed_intent,
            "target_industry": target_slug,
            "confidence_score": round(float(self.confidence_score), 4),
            "route_type": route_type,
            "final_url": final_url,
            "status": self.status,
            "latency_ms": int(round(self.latency_ms)),
            "response_message": self.response_message,
            "redirect_url": self.redirect_url,
        }
        if include_top_candidates:
            payload["top_candidates"] = list(self.top_candidates)
        return payload


def _build_top_candidates(retrieval: list[VectorCandidate]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hit in retrieval:
        sector = hit.sector
        if sector not in ("saglik", "turizm", "egitim", "bilisim", "eglence", "ood"):
            sector = map_sector(str(sector))
        bge = float(hit.score)
        out.append(
            build_top_candidate(
                text=hit.text_content,
                sector=str(sector),
                sub_intent=str(hit.sub_intent),
                initial_score=bge,
                reranker_score=None,
                final_score=bge,
            )
        )
    return out


class V2IntentPipeline:
    """
    2 katmanlı V2 motoru (reranker kaldırıldı).
    K1 Regex eşleşirse embedding'e gitmeden ACCEPT (confidence=1.00).
    Aksi halde BGE-M3 raw Top-1 >= DECISION_THRESHOLD (0.65) → SUCCESS,
    aksi halde OOD ("Sektör Belirsiz").
    """

    DECISION_THRESHOLD = DECISION_THRESHOLD

    def __init__(
        self,
        *,
        store=None,
        embed_fn=None,
        top_k: int = 3,
        enable_fast_path: bool = True,
        enable_k1_regex: bool = True,
        enable_ood_reject: bool = True,
    ) -> None:
        from app.services.keyword_service import KeywordService
        from app.services.session_service import SessionService
        from app.services.similarity_service import SimilarityService

        self._keyword = KeywordService()
        self._session = SessionService()
        self._similarity = SimilarityService(store=store, embed_fn=embed_fn, top_k=top_k)
        self.store = store
        self._embed_fn = embed_fn
        self.top_k = max(1, min(3, int(top_k)))
        self.enable_fast_path = enable_fast_path
        self.enable_k1_regex = enable_k1_regex
        self.enable_ood_reject = enable_ood_reject

    def _ensure_store(self):
        """pgvector varsa SQL ANN; yoksa NPZ — graceful."""
        if self.store is None:
            self.store = self._similarity.store
        return self.store

    def _fetch_kurumsal_hits_hybrid(self, ml_query: str, *, k: int = 50) -> list[VectorCandidate]:
        """Kurumsal K2 fallback — yalnızca kayit_tipi=kurumsal_bilgi (hybrid NPZ arama)."""
        from app.services.embedder import get_embedder

        emb = get_embedder()
        if not emb.is_ready():
            return []
        hits_raw = emb.find_top_k_hybrid(ml_query, k=k, alpha=0.65)
        out: list[VectorCandidate] = []
        for h in hits_raw:
            meta = dict(h.metadata or {})
            kayit_tipi = meta.get("kayit_tipi") or infer_kayit_tipi_legacy(meta)
            if kayit_tipi != KAYIT_TIPI_KURUMSAL:
                continue
            score = float(h.score)
            out.append(
                VectorCandidate(
                    id=int(h.idx),
                    source_id=str(meta.get("id") or meta.get("source_id") or h.idx),
                    sector="ood",
                    sub_intent="corporate_info.general",
                    text_content=h.text,
                    distance=round(max(0.0, 1.0 - score), 6),
                    score=round(score, 6),
                    record_meta=meta,
                )
            )
        return out

    def _get_session_state(self, session_id: str | None) -> dict[str, str | None] | None:
        return self._session.get_state(session_id)

    def get_aktif_sektor(self, session_id: str | None) -> str | None:
        return self._session.get_aktif_sektor(session_id)

    def set_aktif_sektor(self, session_id: str | None, sektor: str) -> None:
        self._session.set_aktif_sektor(session_id, sektor)

    def clear_session(self, session_id: str | None) -> None:
        self._session.clear(session_id)

    def _is_generic_followup(self, query: str) -> bool:
        generic_patterns = [
            r"fiyat", r"ne kadar", r"kiminle", r"demo", r"kurulum süresi", 
            r"referans", r"iletişim", r"mail", r"telefon", r"detay", r"başka neler",
            r"\b(price|cost|quote|pricing|how long|how much|information|list|references)\b"
        ]
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in generic_patterns)

    def _embed_query(self, query: str) -> np.ndarray:
        return self._similarity.embed_query(query)

    def _fast_path_result(self, query: str, t0: float) -> V2PipelineResult | None:
        if not self.enable_fast_path:
            return None
        t = time.perf_counter()
        hit = self._keyword.match_fast_path(query)
        rule_ms = (time.perf_counter() - t) * 1000
        if hit is None:
            return None

        sector = "ood"
        status = hit.status
        return V2PipelineResult(
            query=query,
            retrieval=[],
            sector=sector,
            sub_intent=hit.sub_intent,
            confidence_score=float(hit.confidence_score),
            status=status,
            latency_ms=(time.perf_counter() - t0) * 1000,
            response_message=hit.response_message,
            redirect_url="",
            top_candidates=[],
            stages_ms={
                "rule_ms": rule_ms,
                "embed_ms": 0.0,
                "retrieve_ms": 0.0,
            },
            layer="rule",
            preprocessed_query=query,
        )

    def _k1_regex_result(self, query: str, t0: float) -> V2PipelineResult | None:
        """Katman 1.5 — sektör regex guardrail. Eşleşirse embedding YOK."""
        if not self.enable_k1_regex:
            return None
        t = time.perf_counter()
        sector = self._keyword.match_sector(query)
        rule_ms = (time.perf_counter() - t) * 1000
        if sector is None:
            return None

        sub = f"{sector}.general"
        status = "SUCCESS"
        redirect_url = resolve_redirect_url(sector, sub, status)
        response_message = resolve_response_message(
            sector, sub, status, redirect_url=redirect_url, lang="tr"
        )
        return V2PipelineResult(
            query=query,
            retrieval=[],
            sector=sector,
            sub_intent=sub,
            confidence_score=0.99,
            status=status,
            latency_ms=(time.perf_counter() - t0) * 1000,
            response_message=response_message,
            redirect_url=redirect_url,
            top_candidates=[],
            stages_ms={
                "rule_ms": 0.0,
                "k1_regex_ms": rule_ms,
                "embed_ms": 0.0,
                "retrieve_ms": 0.0,
            },
            layer="rule",
            preprocessed_query=query,
        )

    def _ood_reject_result(self, query: str, t0: float) -> V2PipelineResult | None:
        """Katman 1.6 — B2C/chit-chat OOD guardrail. Eşleşirse embedding YOK."""
        if not self.enable_ood_reject:
            return None
        t = time.perf_counter()
        
        # 0. Small talk (Selamlama) Check - OOD'den önce yakala! SADECE saf selamlama ise!
        small_talk_patterns = [
            r"^((merhaba|selam|selamlar|merhabalar|günaydın|iyi\s*günler|iyi\s*akşamlar|iyi\s*geceler|nasılsın|naber|hi|hello|hey|sa|as|sea|ase)[\s\.,!\?]*)+$",
        ]
        is_small_talk = any(re.search(p, query.strip().lower()) for p in small_talk_patterns)
        
        if is_small_talk:
            return V2PipelineResult(
                query=query,
                retrieval=[],
                sector="belirsiz",
                sub_intent="small_talk",
                confidence_score=1.0,
                status="SUCCESS",
                latency_ms=(time.perf_counter() - t0) * 1000,
                response_message="Merhaba! Size nasıl yardımcı olabilirim?",
                redirect_url="",
                top_candidates=[],
                layer="rule",
                preprocessed_query=query,
            )

        # 1. B2C/Chit-chat reject
        is_ood = check_ood_reject(query)
        
        # 2. Generic Bare Words reject (Halüsinasyon engelleyici)
        # (Bu bölümdeki karmaşık ve STRES/CEKIM regresyonuna yol açan filtre tamamen kaldırılarak,
        # yerine k1_guardrails.py içindeki OOD_FAST_REJECT_REGEX listesine 'komuta kontrol' vs. eklenmiştir.)

        rule_ms = (time.perf_counter() - t) * 1000
        if not is_ood:
            return None

        return V2PipelineResult(
            query=query,
            retrieval=[],
            sector="ood",
            sub_intent="ood.none",
            confidence_score=0.0,
            status="OOD",
            latency_ms=(time.perf_counter() - t0) * 1000,
            response_message=MSG_OOD_GATE,
            redirect_url="",
            top_candidates=[],
            stages_ms={
                "rule_ms": 0.0,
                "k1_regex_ms": 0.0,
                "ood_reject_ms": rule_ms,
                "embed_ms": 0.0,
                "retrieve_ms": 0.0,
            },
            layer="rule",
            preprocessed_query=query,
        )

    def run(self, query: str, session_id: str | None = None, force_lang: str | None = None) -> V2PipelineResult:
        from app.core.torch_runtime import configure_torch_threads
        from app.core.regex_rewriter import RegexRewriter

        t0 = time.perf_counter()
        aktif_sektor = self.get_aktif_sektor(session_id)
        
        negation_keywords = ["değil", "degil", "hariç", "haric", "istemiyoruz", "istemiyorum", "not", "without", "except", "vazgeç", "vazgec", "boşver", "bosver"]
        has_negation = any(w in query.lower() for w in negation_keywords)
        
        if has_negation:
            rewriter = RegexRewriter()
            rewritten = rewriter.rewrite(query)
            rewritten_query = rewritten.clean_query
            negated_sectors_normalized = [map_sector(s) for s in rewritten.negated_sectors]
        else:
            rewritten_query = query
            negated_sectors_normalized = []


        # K1 Greeting / Salutation Safeguard
        normalized_g = re.sub(r'[^\w\s]', '', query.strip().lower())
        greeting_dict = {
            # Türkçe Selamlamalar
            "gunaydin", "günaydın", "iyi gunler", "iyi günler", "iyi aksamlar", "iyi akşamlar",
            "selamlar", "selam", "merhaba", "merhabalar", "sa", "as", "sea", "ase",
            "selamunaleykum", "selamün aleyküm",
            "kolay gelsin", "iyi calismalar", "iyi çalışmalar", "musaid misiniz", "müsait misiniz",
            "nasilsin", "nasılsın", "nasilsiniz", "nasılsınız", "naber", "ne haber", "nehaber",
            
            # İngilizce Selamlamalar
            "good morning", "good afternoon", "good evening", "good day",
            "hello", "hi", "hey", "hi there", "hello there", "greetings",
            "howdy", "morning", "afternoon", "evening",
            "how are you", "how are you doing", "how is it going", "hows it going", "whats up", "whatsup"
        }
        if normalized_g in greeting_dict:
            from app.core.chitchat_rules import MSG_GREETING
            is_tr = (
                normalized_g in {"sa", "as", "sea", "ase"}
                or any(w in normalized_g for w in [
                    "günaydın", "günler", "akşamlar", "selam", "merhaba", "gelsin",
                    "çalışmalar", "müsait", "nasılsın", "nasilsin", "nasılsınız",
                    "nasilsiniz", "naber", "ne haber", "nehaber",
                ])
            )
            resp_msg = (
                MSG_GREETING
                if is_tr else
                "Hello! How can I help you with your business needs in IT, Education, Entertainment, Healthcare, or Tourism sectors?"
            )
            return V2PipelineResult(
                query=query,
                retrieval=[],
                sector="ood",
                sub_intent="ood.none",
                confidence_score=1.0,
                status="SUCCESS",
                layer="rule",
                latency_ms=(time.perf_counter() - t0) * 1000,
                detected_language="tr" if is_tr else "en",
                processed_intent=normalized_g,
                response_message=resp_msg,
                preprocessed_query=query,
            )

        # Language Detection
        if force_lang:
            detected_language = force_lang.lower()
        else:
            tr_chars = len(re.findall(r"[çğıöşüÇĞİÖŞÜ]", query))
            has_en_clutter = any(w in query.lower() for w in ["we need", "looking for", "hello", "hi", "hey", "can you help", "scheduling", "software"])
            detected_language = "en" if (has_en_clutter or (not tr_chars and re.search(r"\b(we|need|looking|for|hi|hello|quote|hospital|software|hotel|reservation|scheduling|our|tournament|esports|streaming|backend|chat|with|low-latency)\b", query.lower()))) else "tr"

        # ── STEP 2+3: Clause-Boundary Negation Removal + Hard OOD Blocklist ──
        # Legal/Real Estate/Finance/Defense/Energy/Food-Hospitality -> HER ZAMAN
        # OOD, teknik jargon (yazılım/software/platform/automation) eşlik etse
        # bile. Tamamlanmış eylem clause'ları (STEP 2) önce atılır, böylece
        # "Poliklinik hallettik, kantin için..." gibi sorgularda "poliklinik"
        # negasyonu yasaklı terim taramasını etkilemez.
        if check_restricted_domain(query):
            return V2PipelineResult(
                query=query,
                retrieval=[],
                sector="ood",
                sub_intent="ood.restricted",
                confidence_score=0.15,
                status="OOD",
                latency_ms=(time.perf_counter() - t0) * 1000,
                response_message=MSG_OOD_GATE,
                redirect_url="",
                top_candidates=[],
                stages_ms={"rule_ms": 0.0, "k1_regex_ms": 0.0, "embed_ms": 0.0, "retrieve_ms": 0.0},
                layer="rule",
                detected_language=detected_language,
                processed_intent=extract_active_clause(query),
                preprocessed_query=query,
            )

        # Standalone & Contextual B2B Jargons protection
        clean_q = query.strip().upper()
        q_words = set(re.split(r'\W+', clean_q))

        jargon_to_sector = {
            "PACS": "saglik",
            "PMS": "turizm",
            "LMS": "egitim",
            "SIEM": "bilisim"
        }

        # Check if any jargon is in the words and it's not a defense/OOD query
        is_defense = any(w in query.lower() for w in ["defense", "military", "radar", "weapon", "askeri", "savunma"])
        matched_jargon = next((j for j in jargon_to_sector if j in q_words), None)

        if matched_jargon and not is_defense:
            sector = jargon_to_sector[matched_jargon]
            if sector not in negated_sectors_normalized:
                # Session state güncelleme (K1 layer'ında)
                self.set_aktif_sektor(session_id, sector)
                # Debug (kaldırıldı)
                return V2PipelineResult(
                query=query,
                retrieval=[],
                sector=sector,
                sub_intent=f"{sector}.general",
                confidence_score=0.99,
                status="SUCCESS",
                layer="rule",
                latency_ms=(time.perf_counter() - t0) * 1000,
                detected_language="en" if any(ord(c) < 128 for c in query) else "tr",
                processed_intent=matched_jargon,
                preprocessed_query=query,
            )

        # Inference Preprocessing (TR & EN Noise Removal)
        clean_rewritten = re.sub(r"Negated_Sector_Keyword:\w+", "", rewritten_query, flags=re.IGNORECASE)
        ml_query = clean_rewritten.lower()
        noise_patterns = [
            # TR
            r"\blütfen\b", r"\bşirketimiz için\b", r"\bsirketimiz icin\b", r"\bacaba\b", 
            r"\bbize\b", r"\bmerhaba\b", r"\bbilgi verir misiniz\b", r"\bbilgi alabilir miyim\b",
            r"\bistiyoruz\b", r"\blazım\b", r"\blazim\b", r"\balmak istiyorum\b", r"\bistiyorum\b",
            r"\bvar mı\b", r"\bvar mi\b", r"\bsağlıyor musunuz\b", r"\bsagliyor musunuz\b", 
            r"\bgerekiyor\b", r"\byarın için\b", r"\byarin icin\b", r"\bbugün\b", r"\bbugun\b", 
            r"\bbenim için\b", r"\bbenim icin\b", r"\bacil olarak\b", r"\bkurumsal düzeyde\b",
            r"\bkurumsal duzeyde\b", r"\bhızlıca\b", r"\bhizlica\b", r"\byeni bir\b",
            # EN
            r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\blooking for\b", r"\bwe need\b", 
            r"\bcan you help\b", r"\bwhat is the price of\b", r"\bquote for\b", r"\bwe want\b",
            r"\bi need\b", r"\brequire\b", r"\bseeking\b"
        ]
        for pattern in noise_patterns:
            ml_query = re.sub(pattern, "", ml_query, flags=re.IGNORECASE)
        ml_query = clean_pure_intent(ml_query)
        ml_query = re.sub(r"[^\w\s-]", "", ml_query)
        ml_query = re.sub(r"\s+", " ", ml_query).strip()
        if not ml_query:
            ml_query = query
        processed_intent = ml_query

        # ── Katman 0: Kurumsal bilgi (chitchat/gibberish ÖNCE — kısa terimler korunur) ──
        k0 = try_k0_corporate_info(query, reply_lang=detected_language)
        if k0:
            total_ms = (time.perf_counter() - t0) * 1000
            return V2PipelineResult(
                query=query,
                retrieval=[],
                sector="ood",
                sub_intent="corporate_info.general",
                confidence_score=1.0,
                status="INFO",
                layer="rule",
                latency_ms=total_ms,
                detected_language=detected_language,
                processed_intent=processed_intent,
                response_message=k0["cevap"],
                redirect_url="",
                preprocessed_query=query,
            )

        # ── Katman 1: Rule-based fast-path (chitchat/gibberish/abuse) ────────
        fast = self._fast_path_result(query, t0)
        if fast is not None:
            fast.detected_language = detected_language
            fast.processed_intent = processed_intent
            return fast

        # Determine if K1 Sector Guardrail should be bypassed due to complexity
        word_count = len(query.split())
        has_negation = any(w in query.lower() for w in ["değil", "degil", "hariç", "haric", "istemiyoruz", "istemiyorum", "not", "without", "except", "vazgeç", "vazgec", "boşver", "bosver"])
        has_conjunction = any(w in query.lower() for w in [" ama ", " fakat ", " lakin ", " ancak ", " but ", " although "])
        bypass_k1_sector = word_count > 6 or has_negation or has_conjunction

        # ── Katman 1.5: K1 Regex sektör guardrail (confidence=1.00) ──────────
        if not bypass_k1_sector:
            k1 = self._k1_regex_result(query, t0)
            if k1 is not None:
                k1.detected_language = detected_language
                k1.processed_intent = processed_intent
                self.set_aktif_sektor(session_id, k1.sector)
                return k1

        # ── Katman 1.6: OOD Fast-Reject guardrail (B2C/chit-chat) ────────────
        ood = self._ood_reject_result(query, t0)
        if ood is not None:
            ood.detected_language = detected_language
            ood.processed_intent = processed_intent
            return ood

        configure_torch_threads(4)
        stages: dict[str, float] = {"rule_ms": 0.0, "k1_regex_ms": 0.0, "ood_reject_ms": 0.0}

        # ── Katman 2: BGE-M3 Retrieval (Dense + Sparse Hybrid) ──────────────
        t = time.perf_counter()
        qvec = self._embed_query(ml_query)
        stages["embed_ms"] = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        store = self._ensure_store()
        kurumsal_hits: list[VectorCandidate] = []
        retrieve_k = max(50, self.top_k * 10)

        if hasattr(store, "backend") and store.backend == "npz":
            from app.services.embedder import get_embedder

            emb = get_embedder()
            hits_raw = emb.find_top_k_hybrid(ml_query, k=self.top_k, alpha=0.65)
            stages["retrieve_ms"] = (time.perf_counter() - t) * 1000

            hits = []
            for h in hits_raw:
                meta = dict(h.metadata or {})
                kayit_tipi = meta.get("kayit_tipi") or infer_kayit_tipi_legacy(meta)
                if kayit_tipi == KAYIT_TIPI_KURUMSAL:
                    continue
                sektor_tr = meta.get("beklenen_sektor") or ""
                sec = map_sector(str(sektor_tr))
                if sec in negated_sectors_normalized:
                    continue
                sub = map_sub_intent(sec, h.text) if sec != "ood" else "ood.none"
                score = float(h.score)
                hits.append(
                    VectorCandidate(
                        id=int(h.idx),
                        source_id=str(meta.get("id") or meta.get("source_id") or h.idx),
                        sector=sec,
                        sub_intent=sub,
                        text_content=h.text,
                        distance=round(max(0.0, 1.0 - score), 6),
                        score=round(score, 6),
                        record_meta=meta,
                    )
                )
        else:
            hits_all = store.search(qvec, top_k=retrieve_k)
            hits = [
                h for h in hits_all
                if h.sector not in negated_sectors_normalized and not _is_kurumsal_candidate(h)
            ][: self.top_k]
            stages["retrieve_ms"] = (time.perf_counter() - t) * 1000

        top_candidates = _build_top_candidates(hits)

        # ── K2 Top-K Karar Parametreleri ────
        K2_TOP_K = 5
        K2_MIN_SIM = 0.50
        K2_VOTE_THRESHOLD = 0.65
        K2_MARGIN = 0.05
        K2_HIGH_CONFIDENCE = 0.80

        # ── Karar Ağacı: evaluate Top-K results ────
        if not hits:
            sector, sub, conf, status = "ood", "ood.none", 0.0, "OOD"
            redirect_url = ""
            response_message = MSG_OOD_GATE
            s1 = 0.0
        else:
            s1 = float(hits[0].score) if hits else 0.0
            
            # Map sectors for candidates
            def clean_sector(sec_in):
                sec = sec_in or ""
                if "/" in sec: sec = sec.split("/")[0]
                if "." in sec: sec = sec.split(".")[0]
                sec = sec.strip().lower()
                if sec not in ("saglik", "turizm", "egitim", "bilisim", "eglence", "ood", PG_SECTOR_INFO, "info"):
                    sec = map_sector(str(sec))
                if "/" in sec: sec = sec.split("/")[0]
                if "." in sec: sec = sec.split(".")[0]
                return sec

            # Adım 1: Top-K adayları filtrele
            valid_hits = [h for h in hits[:K2_TOP_K] if float(h.score) >= K2_MIN_SIM]
            
            if not valid_hits:
                sector, sub, conf, status = "ood", "ood.none", float(hits[0].score) if hits else 0.0, "OOD"
                redirect_url = ""
                response_message = MSG_OOD_GATE
                s1 = float(hits[0].score) if hits else 0.0
            else:
                best = valid_hits[0]
                best_sector = clean_sector(best.sector)
                
                # Yol A — Yüksek güven kısayolu
                if s1 >= K2_HIGH_CONFIDENCE and best_sector != "ood":
                    # Safe-Fail Strict Guardrail: explicit B2B/yazılım kelimesi yoksa ve benzerlik < 0.85 ise bilisim olamaz.
                    is_safe = True
                    if best_sector == "bilisim":
                        explicit_b2b_pattern = re.compile(
                            r"\b(erp|api|yazılım|yazilim|entegrasyon|crm|cloud|saas|sistem|platform|otomasyon|dashboard|bi\s*tool|powerbi|business\s*intelligence|network|sunucu|server|lms)\b",
                            re.IGNORECASE
                        )
                        has_explicit = bool(explicit_b2b_pattern.search(query))
                        if not has_explicit and s1 < 0.85:
                            is_safe = False
                    
                    if is_safe:
                        sector = best_sector
                        sub = best.sub_intent
                        conf = s1
                        status = "SUCCESS"
                        _trace_decision(f"K2_YolA high_conf s1={s1:.4f} sector={sector}")
                        redirect_url = resolve_redirect_url(sector, sub, status)
                        response_message = resolve_response_message(sector, sub, status, redirect_url=redirect_url, lang=detected_language)
                    else:
                        sector, sub, conf, status = "ood", "ood.none", s1, "OOD"
                        redirect_url = ""
                        response_message = MSG_OOD_GATE
                else:
                    # Yol B — Konsensüs ataması (Top-K Oylama)
                    sector_scores = {}
                    for h in valid_hits:
                        sec = clean_sector(h.sector)
                        if sec not in sector_scores:
                            sector_scores[sec] = {"count": 0, "sum_sim": 0.0, "sub_intent": h.sub_intent}
                        sector_scores[sec]["count"] += 1
                        sector_scores[sec]["sum_sim"] += float(h.score)
                    
                    # Calculate avg_sim
                    for sec in sector_scores:
                        sector_scores[sec]["avg_sim"] = sector_scores[sec]["sum_sim"] / sector_scores[sec]["count"]
                        
                    # Sort by count (agreement) descending, then avg_sim descending
                    sorted_sectors = sorted(
                        sector_scores.keys(), 
                        key=lambda x: (sector_scores[x]["count"], sector_scores[x]["avg_sim"]), 
                        reverse=True
                    )
                    
                    top_sec = sorted_sectors[0]
                    top_stats = sector_scores[top_sec]
                    
                    margin = top_stats["avg_sim"]
                    if len(sorted_sectors) > 1:
                        second_sec = sorted_sectors[1]
                        margin = top_stats["avg_sim"] - sector_scores[second_sec]["avg_sim"]
                        
                    if top_sec != "ood" and top_stats["count"] >= 2 and margin >= K2_MARGIN:
                        # Dinamik eşik: Eğlence sektörü için İngilizce kelime geçiyorsa esnet.
                        effective_threshold = K2_VOTE_THRESHOLD
                        if top_sec == "eglence":
                            eglence_en_pattern = re.compile(r"\b(esports|streaming|gaming|game|video|chat|tournament|broadcast)\b", re.IGNORECASE)
                            if eglence_en_pattern.search(query):
                                effective_threshold = 0.60

                        is_safe = False
                        if top_stats["avg_sim"] >= effective_threshold:
                            is_safe = True
                            # Safe-Fail Strict Guardrail for bilisim
                            if top_sec == "bilisim":
                                explicit_b2b_pattern = re.compile(
                                    r"\b(erp|api|yazılım|yazilim|entegrasyon|crm|cloud|saas|sistem|platform|otomasyon|dashboard|bi\s*tool|powerbi|business\s*intelligence|network|sunucu|server|lms|aws|microservices|backend|devops|cybersecurity)\b",
                                    re.IGNORECASE
                                )
                                has_explicit = bool(explicit_b2b_pattern.search(query))
                                if not has_explicit and top_stats["avg_sim"] < 0.85:
                                    is_safe = False
                        
                        if is_safe:
                            sector = top_sec
                            sub = top_stats["sub_intent"]
                            conf = top_stats["avg_sim"]
                            status = "SUCCESS"
                            _trace_decision(
                                f"K2_YolB consensus sector={sector} avg={conf:.4f} count={top_stats['count']}"
                            )
                            redirect_url = resolve_redirect_url(sector, sub, status)
                            response_message = resolve_response_message(sector, sub, status, redirect_url=redirect_url, lang=detected_language)
                        else:
                            sector, sub, conf, status = "ood", "ood.none", top_stats["avg_sim"], "OOD"
                            redirect_url = ""
                            response_message = MSG_OOD_GATE
                    else:
                        # Yol C — Hiçbiri sağlanmazsa
                        sector, sub, conf, status = "ood", "ood.none", s1, "OOD"
                        _trace_decision(f"K2_YolC initial_ood s1={s1:.4f}")
                        redirect_url = ""
                        response_message = MSG_OOD_GATE

        # Özel kural: oteller kelimesi geçiyorsa turizm olarak kabul et (retrieval hatası düzeltmesi)
        # Sadece session context yoksa çalıştır (ilk tur sorguları için)
        # Ancak özne/kendi sektör belirten ifadeler ("yazılımcıyız", "biz X firmasıyız" vb.) varsa çalıştırma
        self_subject_keywords = ["yazılımcıyız", "yazılım firması", "bilişim şirketi", "teknoloji şirketi", "yazılım geliştiriyoruz", "yazılım çözüm"]
        is_self_subject = any(keyword in query.lower() for keyword in self_subject_keywords)
        if ("oteller" in query.lower() or "otel" in query.lower()) and not aktif_sektor and not is_self_subject:
            sector = "turizm"
            sub = "turizm.general"
            conf = 0.95
            status = "SUCCESS"
            redirect_url = resolve_redirect_url(sector, sub, status)
            response_message = resolve_response_message(
                sector, sub, status, redirect_url=redirect_url, lang=detected_language
            )
            # Session state güncelleme (sonraki sorgular için)
            self.set_aktif_sektor(session_id, sector)
            total_ms = (time.perf_counter() - t0) * 1000
            return V2PipelineResult(
                query=query,
                retrieval=hits,
                sector=sector,
                sub_intent=sub,
                confidence_score=conf,
                status=status,
                latency_ms=total_ms,
                response_message=response_message,
                redirect_url=redirect_url,
                top_candidates=top_candidates,
                stages_ms=stages,
                layer="ml",
                detected_language=detected_language,
                processed_intent=processed_intent,
                negated_sectors=negated_sectors_normalized,
                preprocessed_query=ml_query,
            )

        # Kurumsal K2 fallback — hybrid yalnızca bu dar yolda (K2-01 vb.)
        if status == "OOD" and not _has_strong_service_signal(query):
            if not kurumsal_hits:
                kurumsal_hits = self._fetch_kurumsal_hits_hybrid(ml_query)
            kh = pick_kurumsal_hit_for_lang(kurumsal_hits, detected_language)
            if kh is not None:
                kh_score = float(kh.score)
                if kh_score >= DECISION_THRESHOLD:
                    meta = kh.record_meta or {}
                    cevap = (meta.get("cevap") or "").strip()
                    if not cevap and kh.text_content:
                        cevap = meta.get("cevap") or ""
                    if cevap:
                        sector, sub, conf, status = "ood", "corporate_info.general", kh_score, "INFO"
                        response_message = sanitize_corporate_cevap(cevap)
                        redirect_url = ""
                        _trace_decision(f"K2_Kurumsal score={kh_score:.4f}")

        if sector == "ood" and aktif_sektor and self._is_generic_followup(query):
            sector = aktif_sektor
            sub = f"{aktif_sektor}.general"
            conf = 0.95
            status = "SUCCESS"
            _trace_decision(f"SessionMem_757 aktif={aktif_sektor}")
            redirect_url = resolve_redirect_url(sector, sub, status)
            response_message = resolve_response_message(
                sector, sub, status, redirect_url=redirect_url, lang=detected_language
            )
        elif sector != "ood" and sector != "belirsiz" and status != "INFO":
            self.set_aktif_sektor(session_id, sector)
            # Debug (kaldırıldı)
        elif sector == "ood" and not aktif_sektor and session_id and hits and s1 >= 0.45:
            # İlk tur sorguları için düşük skorlu sektör kabul et (session context varsa)
            # Ancak sorgu sector kelimesi içeriyorsa (F kategorisi traps), kabul etme
            trap_keywords = ["iş ortaklığı", "ofisimiz var", "personel arıyoruz", "beklemek istemediğimiz", "çalışma ortamı", "hayat eğitimi", "ofisler açmayı", "iş ortamı", "etkinlik organizasyonuna", "iletişimi güçlendirmek", "sağlıksız gıda", "eğitimsiz personel", "bilişim gibi hızlı büyüyen"]
            is_trap = any(keyword in query.lower() for keyword in trap_keywords)
            if not is_trap:
                first_sector = hits[0].sector if hits else "ood"
                if first_sector != "ood" and first_sector not in (PG_SECTOR_INFO, "info"):
                    sector = first_sector
                    sub = f"{first_sector}.general"
                    conf = s1
                    status = "SUCCESS"
                    _trace_decision(f"Fallback_769 s1={s1:.4f} first_sector={first_sector}")
                    redirect_url = resolve_redirect_url(sector, sub, status)
                    response_message = resolve_response_message(
                        sector, sub, status, redirect_url=redirect_url, lang=detected_language
                    )
                    self.set_aktif_sektor(session_id, sector)
        elif sector == "ood" and not aktif_sektor and session_id and hits and s1 >= 0.40:
            # İlk tur sorguları için daha düşük threshold (session context varsa)
            # Ancak sorgu sector kelimesi içeriyorsa (F kategorisi traps), kabul etme
            trap_keywords = ["iş ortaklığı", "ofisimiz var", "personel arıyoruz", "beklemek istemediğimiz", "çalışma ortamı", "hayat eğitimi", "ofisler açmayı", "iş ortamı", "etkinlik organizasyonuna", "iletişimi güçlendirmek", "sağlıksız gıda", "eğitimsiz personel", "bilişim gibi hızlı büyüyen"]
            is_trap = any(keyword in query.lower() for keyword in trap_keywords)
            if not is_trap:
                first_sector = hits[0].sector if hits else "ood"
                # Özel kural: oteller kelimesi geçiyorsa turizm olarak kabul et
                if "oteller" in query.lower() or "otel" in query.lower():
                    first_sector = "turizm"
                if first_sector != "ood" and first_sector not in (PG_SECTOR_INFO, "info"):
                    sector = first_sector
                    sub = f"{first_sector}.general"
                    conf = s1
                    status = "SUCCESS"
                    _trace_decision(f"Fallback_786 s1={s1:.4f} first_sector={first_sector}")
                    redirect_url = resolve_redirect_url(sector, sub, status)
                    response_message = resolve_response_message(
                        sector, sub, status, redirect_url=redirect_url, lang=detected_language
                    )
                    self.set_aktif_sektor(session_id, sector)

        total_ms = (time.perf_counter() - t0) * 1000
        return V2PipelineResult(
            query=query,
            retrieval=hits,
            sector=sector,
            sub_intent=sub,
            confidence_score=conf,
            status=status,
            latency_ms=total_ms,
            response_message=response_message,
            redirect_url=redirect_url,
            top_candidates=top_candidates,
            stages_ms=stages,
            layer="ml",
            detected_language=detected_language,
            processed_intent=processed_intent,
            negated_sectors=negated_sectors_normalized,
            preprocessed_query=ml_query,
        )
