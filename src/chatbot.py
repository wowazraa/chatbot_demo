"""
Chatbot motoru — BGE-öncelikli eşik politikası + ASCII / kısaltma / session hafıza.

Politika: emin değilse FB (yanlış sektöre gitme); basit-açık cümlede K1/K2.

Öncelik sırası (kesin):
  1) Kullanıcı sorgusu → normalize / selamlama temizliği / ASCII
  2) Kurumsal kısaltma sözlüğü → K1 (skor=1.00, BGE'ye gitmeden sektör)
  3) BGE-M3 indeks araması
  4) skor >= MIN_BGE (0.80) ve sektör margin yeterli → K2 + aktif_sektor
  5) skor yüksek ama iki sektör yakın → FB (yanlış > sessizlik)
  6) skor < 0.80 ve sorgu jenerik ise → session HAFIZA
  7) Aksi halde → FB güvenlik ağı
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.llm_rewriter import LLMRewriter, RewriteResult

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_DATASET = "chatbot_dataset_augmented.json"  # fallback; asıl yol router_config


def _default_corpus_path() -> Path:
    try:
        from src.router_config import active_paths

        return active_paths()["corpus"]  # type: ignore[return-value]
    except Exception:
        return PROCESSED_DIR / DEFAULT_DATASET


def _default_index_dir() -> Path:
    try:
        from src.router_config import active_paths

        return active_paths()["index_dir"]  # type: ignore[return-value]
    except Exception:
        return PROCESSED_DIR


# Tek karar eşiği — false positive'e karşı yüksek bar
LEGACY_MIN_BGE = 0.71
MIN_BGE = LEGACY_MIN_BGE
# Top-1 ile farklı sektördeki top-2 arası fark bunun altındaysa → FB (yanlış sektöre gitme)
MIN_MARGIN = 0.06

FB_NETLESTIRME_MSG = (
    "Talebinizi net anlayamadım. Hangi sektör / süreç için "
    "destek aradığınızı kısaca yazar mısınız?"
)

FB_MSG_GREETING = (
    "Merhaba! Size nasıl yardımcı olabilirim? "
    "Hangi sektör veya süreç için destek arıyorsunuz?"
)

FB_MSG_THANKS = (
    "Rica ederim! Yardımcı olabildiysem ne mutlu. "
    "Farklı bir sektör veya süreç için destek arıyorsanız belirtebilirsiniz."
)

# Kurumsal kısaltma → sektör (yalnızca net kısaltmalar; jenerik kelime YOK)
# 'randevu/otel/burs/hastane' gibi tekiller ML'ye bırakılır (ezber riski).
KISALTMALAR: dict[str, str] = {
    "obs": "egitim",
    "lms": "egitim",
    "öbys": "egitim",
    "hbys": "saglik",
    "enabiz": "saglik",
    "ahbs": "saglik",
    "pnr": "turizm",
    "api": "bilisim",
    "sdk": "bilisim",
    "saas": "bilisim",
    "ott": "eglence",
}

# Uzun / zengin cümleler K1 short-circuit'e girmez → Katman 2 (ML)
_K1_MAX_TOKENS = 5

# Bilinen yazım bozulmaları → kanonik token (normalize / BGE öncesi)
_TYPO_TOKEN_MAP: dict[str, str] = {
    "randvu": "randevu",
    "randv": "randevu",
    "randev": "randevu",
    "randevuu": "randevu",
    "hastne": "hastane",
    "hstane": "hastane",
    "hastan": "hastane",
    "doktr": "doktor",
    "poliklnik": "poliklinik",
}

_WS = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_TR_TO_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")

# ASCII-fold lookup (öbys → obys)
_KISALTMA_LOOKUP: dict[str, str] = {
    (k.translate(_TR_TO_ASCII).lower()): v for k, v in KISALTMALAR.items()
}

# Cümle başından atılacak selamlama / nezaket gürültüsü (uzun → kısa)
GREETING_NOISE: tuple[str, ...] = (
    "kolay gelsin",
    "iyi akşamlar",
    "iyi aksamlar",
    "merhabalar",
    "merhaba",
    "selamlar",
    "selam",
    "ya",
)

# Arama seed'lerinde atılacak nezaket dolgusu (etiket ezberi degil; sorguyu oze indirger)
_FILLER_PHRASES: tuple[str, ...] = (
    "yardimci olur musunuz",
    "yardımcı olur musunuz",
    "bilgi verir misiniz",
    "rica etsem",
    "lutfen",
    "lütfen",
    "acaba",
    "acil",
    "musait misiniz",
    "bakar misiniz",
    "bakar mısınız",
)


# ---------------------------------------------------------------------------
# Yanıt
# ---------------------------------------------------------------------------
@dataclass
class ChatbotResponse:
    """Chatbot'un tek bir sorguya verdiği yanıt (UI sözleşmesi korunur)."""

    girdi: str
    normalize_girdi: str
    sektor: str                       # tespit edilen sektör veya belirsiz
    mod: str                          # K1 | K2 | HAFIZA | FB
    skor: float                       # BGE skoru (FB olsa bile gerçek skor korunur)
    yontem: str                       # "bge-m3" | "kisaltma" | "hafiza" | "fb"
    lang: str = "tr"
    eslesen_mesaj: str = ""
    eslesen_id: Any = None
    aciklama: str = ""
    temiz_sorgu: str = ""
    rewrite_backend: str = ""
    negated_sectors: list[str] = field(default_factory=list)
    masked_sectors: list[str] = field(default_factory=list)
    inspector_label: str = ""
    k1_hints: dict[str, Any] = field(default_factory=dict)
    yanit_mesaji: str = ""  # kullanıcıya gösterilecek bağlamsal metin (özellikle FB)
    # Demo tek-kanal: BGE Top-3 (ikinci retrieval yok)
    top_candidates: list[dict[str, Any]] = field(default_factory=list)

    def to_intent_router(
        self,
        latency_ms: float | int | None = None,
        seed_intent_code: str | None = None,
        top_candidates: list[dict[str, Any]] | None = None,
        include_top_candidates: bool = False,
        candidates: list[dict[str, Any]] | None = None,
        include_candidates: bool = False,
    ) -> dict[str, Any]:
        """Spec JSON + response_* / optional top_candidates."""
        from src.intent_router_contract import to_intent_router_json

        return to_intent_router_json(
            self,
            latency_ms=latency_ms,
            seed_intent_code=seed_intent_code,
            top_candidates=top_candidates if top_candidates is not None else candidates,
            include_top_candidates=include_top_candidates or include_candidates,
        )


# ---------------------------------------------------------------------------
# Ön işleme — yüzey temizliği + ASCII hizalama (sınıflandırma / FB değil)
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    t = (text or "").strip().lower()
    t = _WS.sub(" ", t)
    return t


def to_ascii(text: str) -> str:
    """Türkçe karakterleri ASCII karşılıklarına çevir."""
    return (text or "").translate(_TR_TO_ASCII)


def apply_typo_fold(text: str) -> str:
    """
    Sınırlı yazım düzeltmesi — yalnızca bilinen randevu/hastane bozulmaları.
    Geniş spell-correct yok.
    """
    raw = text or ""
    if not raw.strip():
        return raw

    def _repl(m: re.Match[str]) -> str:
        tok = m.group(0)
        folded = to_ascii(tok).lower()
        canon = _TYPO_TOKEN_MAP.get(folded)
        if not canon:
            return tok
        # Orijinal kasıt/TR karakter korunmaz; kanonik ASCII-TR karışımı yeterli
        return canon

    return _TOKEN_RE.sub(_repl, raw)


def match_kisaltma(text: str) -> tuple[str, str] | None:
    """
    Yalnızca kurumsal kısaltma (OBS/LMS/HBYS/…) — tek sektöre işaret ederse K1.
    Jenerik kelime (randevu/otel/burs) ve uzun zengin cümleler → None (ML).
    """
    folded = to_ascii(_normalize(text)).lower()
    if not folded:
        return None

    tokens = _TOKEN_RE.findall(folded)
    if not tokens or len(tokens) > _K1_MAX_TOKENS:
        return None

    sektorler: dict[str, str] = {}
    for tok in tokens:
        sek = _KISALTMA_LOOKUP.get(tok)
        hit_key = tok if sek else None
        if sek is None:
            for key, sektor in _KISALTMA_LOOKUP.items():
                if len(key) >= 4 and tok.startswith(key):
                    sek = sektor
                    hit_key = key
                    break
        if sek and hit_key:
            sektorler[sek] = hit_key

    if len(sektorler) != 1:
        return None
    sektor, kisaltma = next(iter(sektorler.items()))
    return sektor, kisaltma


def strip_filler_phrases(text: str) -> str:
    """Nezaket dolgusunu cikarir (sektor etiketi vermez; sadece arama ozunu netlestirir)."""
    t = _normalize(text)
    if not t:
        return t
    folded = to_ascii(t).lower()
    # uzun → kisa
    for phrase in sorted(_FILLER_PHRASES, key=len, reverse=True):
        p = to_ascii(phrase).lower()
        if not p:
            continue
        folded = re.sub(rf"\b{re.escape(p)}\b", " ", folded)
    # orijinal TR metinde de ayni pencereleri kaba sil
    out = t
    for phrase in sorted(_FILLER_PHRASES, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(phrase)}\b", " ", out, flags=re.IGNORECASE)
        out = re.sub(
            rf"\b{re.escape(to_ascii(phrase))}\b", " ", out, flags=re.IGNORECASE
        )
    out = _normalize(out)
    return out if out else t


def fallback_user_message(text: str) -> str:
    """
    FB kararı için bağlamsal kullanıcı mesajı.
    Teşekkür, selamlama'dan önce gelir (örn. 'teşekkürler iyi akşamlar').
    Domain sinyali varsa selam/teşekkür substring'i ezmesin.
    """
    folded = to_ascii(_normalize(text)).lower()

    # İçerikli talep → genel netleştirme (selamlar+hastane greeting olmasın)
    if _DOMAIN_CONTENT_RE.search(folded):
        return FB_NETLESTIRME_MSG

    if re.search(r"\b(tesekkurler|tesekkur|sagol|sag\s+olun|sag\s+ol)\b", folded):
        return FB_MSG_THANKS

    if re.search(
        r"\b(merhabalar|merhaba|selamlar|selam|iyi\s+gunler|iyi\s+aksamlar)\b",
        folded,
    ):
        return FB_MSG_GREETING

    return FB_NETLESTIRME_MSG


# Jenerik / sektörsüz takip soruları (kısa takip: fiyat, demo…)
_GENERIC_FOLLOWUP_RE = re.compile(
    r"(?:"
    r"\bfiyat\w*|\bteklif\b|\bdemo\b|\breferans\w*"
    r"|\bsure\b|\bsurer\b|\bkurulum\b|\bdestek\b"
    r"|\bpaket\b|\bhizmet\b|\bgorus\w*|\biletisim\b|\bneler\b"
    r"|\bmail\b|\bofis\b|\badres\b|\bkiminle\b"
    r"|\byazilim hizmet|\bne\s+kadar\b"
    r"|\bdaha\s+bilgi\b|\bbilgi\s+alabilir\b|\bbilgi\s+verir\b"
    r")",
    re.IGNORECASE,
)

# Bu sinyaller varsa sorgu "icerikli"dir → HAFIZA ezmesin
_DOMAIN_CONTENT_RE = re.compile(
    r"(?:"
    r"hastane|hekim|poliklinik|klinik|randevu|tahlil|kardiyoloji|"
    r"hasta|nobet|eczane|teletip|hbys|"
    r"otel|rezervasyon|seyahat|acente|muze|check[\s-]?in|pnr|bilet|"
    r"siber|kodlama|sunucu|veritabani|medya|etkinlik|konser|ott|streaming|yayin|"
    r"egitim|ogrenim|ogrenci|ders|kutuphane|universite|lms|obs|fakult"
    r")",
    re.IGNORECASE,
)

# Saf selamlama / teşekkür — HAFIZA ile ezilmesin (bağlamsal FB kalsın)
_PURE_SOCIAL_RE = re.compile(
    r"^(?:"
    r"merhaba|selam|selamlar|merhabalar|"
    r"iyi\s+gunler|iyi\s+aksamlar|iyi\s+akşamlar|"
    r"tesekkurler|tesekkur|sagol|rica\s+ederim"
    r")[\s!.?]*$",
    re.IGNORECASE,
)


def is_generic_followup(text: str) -> bool:
    """
    Sektörsüz kısa takip mi? (fiyat, demo…)
    Uzun veya domain sinyalli sorgular HAFIZA'ya düşmez
    (örn. 'askeri lojistik… nasıl' oturum turizmini ezmesin).
    """
    folded = to_ascii(_normalize(text)).lower()
    if not folded or _PURE_SOCIAL_RE.match(folded):
        return False
    tokens = _TOKEN_RE.findall(folded)
    if len(tokens) > 8:
        return False
    if _DOMAIN_CONTENT_RE.search(folded):
        return False
    return bool(_GENERIC_FOLLOWUP_RE.search(folded))


def hafiza_user_message(sektor: str) -> str:
    return (
        f"{sektor} sektörü bağlamında devam ediyorum. "
        "Demo, fiyat veya detaylı bilgi için ilgili ekiple ilerleyebiliriz."
    )


def _noise_phrase_regex(phrase: str) -> str:
    """TR/ASCII fold toleranslı tek gürültü ifadesi (ör. akşamlar|aksamlar)."""
    parts: list[str] = []
    for ch in phrase:
        a = to_ascii(ch)
        if ch == " ":
            parts.append(r"\s+")
        elif ch != a:
            parts.append(f"[{re.escape(ch)}{re.escape(a)}]")
        else:
            parts.append(re.escape(ch))
    return "".join(parts)


def _build_leading_noise_re(phrases: tuple[str, ...] = GREETING_NOISE) -> re.Pattern[str]:
    ordered = sorted(phrases, key=len, reverse=True)
    alt = "|".join(_noise_phrase_regex(p) for p in ordered)
    # Başta: ifade + ayırıcı (boşluk / noktalama); tekrarlı soyma için
    return re.compile(
        rf"^(?:{alt})(?:\s*[,\.!?;:]+\s*|\s+)+",
        re.IGNORECASE,
    )


_LEADING_NOISE_RE = _build_leading_noise_re()


def strip_leading_noise(text: str) -> str:
    """
    Sorgunun başındaki selamlama/nezaket gürültüsünü at.
    Örnek: 'Ya merhaba iyi aksamlar hekim takvimi ariyoruz'
         → 'hekim takvimi ariyoruz'
    Saf selamlama (kalan boş) ise orijinal metni korur.
    """
    original = _normalize(text)
    if not original:
        return original

    t = original
    for _ in range(16):
        m = _LEADING_NOISE_RE.match(t)
        if not m:
            break
        t = _normalize(t[m.end() :])

    return t if t else original


def query_search_variants(text: str) -> list[str]:
    """BGE aramasında denenecek hafif metin varyantları (eşik değişmez)."""
    base = _normalize(text)
    if not base:
        return []

    variants: list[str] = []
    seen: set[str] = set()

    def _add(v: str) -> None:
        v = _normalize(v)
        if v and v not in seen:
            seen.add(v)
            variants.append(v)

    _add(base)
    core = strip_filler_phrases(base)
    _add(core)
    ascii_q = to_ascii(base)
    _add(ascii_q)
    _add(to_ascii(core))
    _add(re.sub(r"\bugra\s+san\b", "ugrasan", ascii_q))
    _add(re.sub(r"\bugrasan\b", "ugra san", ascii_q))
    _add(re.sub(r"\btele[\s]?tip\b", "tele-tip", ascii_q))
    _add(re.sub(r"\btele-tip\b", "tele tip", ascii_q))
    return variants


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------
class Chatbot:
    """
    Kullanım:
        bot = Chatbot()
        yanit = bot.sor("Hastane yönetim sistemi arıyoruz")
    """

    MIN_BGE = LEGACY_MIN_BGE
    MIN_MARGIN = MIN_MARGIN
    ALPHA = 0.65  # dense/sparse hibrit ağırlığı (embedder)

    def __init__(
        self,
        dataset_path: Path | None = None,
        index_dir: Path | None = None,
        force_simulated_rewriter: bool = False,
    ) -> None:
        self._path = dataset_path or _default_corpus_path()
        self._index_dir = index_dir or _default_index_dir()
        self._kayitlar: list[dict[str, Any]] = []
        self._embedder = None
        self._rewriter = LLMRewriter(force_simulated=force_simulated_rewriter)
        # session_id → {"aktif_sektor": str | None}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._yukle()

    def _session_state(self, session_id: str | None) -> dict[str, Any] | None:
        if not session_id:
            return None
        if session_id not in self._sessions:
            self._sessions[session_id] = {"aktif_sektor": None}
        return self._sessions[session_id]

    def get_aktif_sektor(self, session_id: str | None) -> str | None:
        st = self._session_state(session_id)
        if not st:
            return None
        sek = st.get("aktif_sektor")
        return str(sek) if sek else None

    def set_aktif_sektor(self, session_id: str | None, sektor: str) -> None:
        st = self._session_state(session_id)
        if st is None:
            return
        if sektor and sektor not in ("", "belirsiz", "?"):
            st["aktif_sektor"] = str(sektor)

    def clear_session(self, session_id: str | None) -> None:
        if session_id and session_id in self._sessions:
            self._sessions.pop(session_id, None)

    def _yukle(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(
                f"İşlenmiş veri seti bulunamadı: {self._path}\n"
                "Önce `src/data_augmented.py` çalıştırın."
            )
        with self._path.open(encoding="utf-8") as f:
            raw = json.load(f)
        recs: list[dict] = raw.get("kayitlar", raw) if isinstance(raw, dict) else raw
        self._kayitlar = recs

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder
        try:
            from src.embedder import get_embedder

            self._embedder = get_embedder(self._index_dir)
        except Exception:
            self._embedder = None
        return self._embedder

    def corpus_boyutu(self) -> int:
        return len(self._kayitlar)

    def bge_aktif_mi(self) -> bool:
        emb = self._get_embedder()
        return emb is not None and emb.is_ready()

    def _best_bge_hit(self, query: str, embedder: Any) -> tuple[Any | None, str, list]:
        """Varyantlar üzerinde ara; en yüksek skorlu hit + kullanılan sorgu + top-k."""
        best = None
        best_results: list = []
        used = query
        for variant in query_search_variants(query):
            results = embedder.find_top_k_hybrid(variant, k=5, alpha=self.ALPHA)
            if not results:
                continue
            hit = results[0]
            if best is None or float(hit.score) > float(best.score):
                best = hit
                best_results = list(results)
                used = variant
        return best, used, best_results

    def _sektor_ambiguous(self, results: list, top_sektor: str, top_skor: float) -> bool:
        """Farklı sektör yakın ikinci sıradaysa emin değiliz → True (FB tercih)."""
        for hit in results[1:]:
            s2 = (hit.metadata or {}).get("beklenen_sektor") or ""
            if s2 in ("", "belirsiz", "?", top_sektor):
                continue
            if top_skor - float(hit.score) < float(self.MIN_MARGIN):
                return True
            break
        return False

    def _hits_to_top_candidates(self, results: list, *, top_k: int = 3) -> list[dict[str, Any]]:
        """Tek BGE retrieval → contract top_candidates (rerank sonra serialize'da)."""
        from src.intent_router_contract import build_top_candidate, map_sector, map_sub_intent

        out: list[dict[str, Any]] = []
        for h in (results or [])[:top_k]:
            sector = map_sector(str((h.metadata or {}).get("beklenen_sektor") or ""))
            text = h.text or ""
            sub = map_sub_intent(sector, text) if sector != "ood" else "ood.none"
            out.append(
                build_top_candidate(
                    text=text,
                    sector=sector,
                    sub_intent=sub,
                    initial_score=float(h.score),
                    reranker_score=None,
                )
            )
        return out

    def _fallback_belirsiz(
        self,
        *,
        kullanici_girdisi: str,
        normalize_girdi: str,
        lang: str,
        clean: str,
        rewrite_backend: str,
        skor: float,
        eslesen_mesaj: str = "",
        eslesen_id: Any = None,
        aciklama: str = "",
        top_candidates: list[dict[str, Any]] | None = None,
    ) -> ChatbotResponse:
        """
        Güvenlik ağı — YALNIZCA BGE emin olamadıktan / hazır olmadıktan sonra.
        Kullanıcıya bağlamsal (selamlama / teşekkür / genel) mesaj döner.
        """
        user_msg = fallback_user_message(kullanici_girdisi)
        prefix = (aciklama or "").strip()
        full_aciklama = f"{prefix} | {user_msg}" if prefix else user_msg

        return ChatbotResponse(
            girdi=kullanici_girdisi,
            normalize_girdi=normalize_girdi,
            sektor="belirsiz",
            mod="FB",
            skor=round(float(skor), 4),
            yontem="fb",
            lang=lang,
            eslesen_mesaj=eslesen_mesaj,
            eslesen_id=eslesen_id,
            aciklama=full_aciklama,
            temiz_sorgu=clean or kullanici_girdisi,
            rewrite_backend=rewrite_backend,
            inspector_label="Sektör Belirsiz",
            yanit_mesaji=user_msg,
            top_candidates=list(top_candidates or []),
        )

    def _yanit_hafiza(
        self,
        *,
        kullanici_girdisi: str,
        normalize_girdi: str,
        sektor: str,
        lang: str,
        clean: str,
        rewrite_backend: str,
        bge_skor: float = 0.0,
    ) -> ChatbotResponse:
        msg = hafiza_user_message(sektor)
        return ChatbotResponse(
            girdi=kullanici_girdisi,
            normalize_girdi=normalize_girdi,
            sektor=sektor,
            mod="HAFIZA",
            skor=1.0,
            yontem="hafiza",
            lang=lang,
            eslesen_mesaj=f"aktif_sektor={sektor}",
            aciklama=(
                f"Session hafıza | aktif_sektor={sektor!r} | "
                f"jenerik takip (BGE={bge_skor:.3f} < {self.MIN_BGE}) → HAFIZA"
            ),
            temiz_sorgu=clean or kullanici_girdisi,
            rewrite_backend=rewrite_backend,
            inspector_label=str(sektor),
            yanit_mesaji=msg,
        )

    def sor(
        self,
        kullanici_girdisi: str,
        session_id: str | None = None,
    ) -> ChatbotResponse:
        from src.v2_pipeline import V2IntentPipeline

        # Pipeline'ı singleton olarak tut
        if not hasattr(self, '_v2_pipeline'):
            self._v2_pipeline = V2IntentPipeline()
        
        res = self._v2_pipeline.run(kullanici_girdisi, session_id=session_id)

        sektor = res.sector
        if sektor == "ood":
            sektor = "belirsiz"

        yontem = "bge-m3"
        if res.layer == "rule":
            yontem = "kisaltma"
        elif res.layer == "memory":
            yontem = "hafiza"

        mod = res.status
        if mod == "OOD":
            mod = "FB"
        elif res.layer == "rule":
            mod = "K1"
        elif res.layer == "ml":
            mod = "K2"
        
        # Session fallback durumunda mod'u HAFIZA olarak ayarla
        # Sadece gerçek session fallback durumunda (aktif_sektor var ve query generic follow-up)
        aktif_sektor = self._v2_pipeline.get_aktif_sektor(session_id) if hasattr(self, '_v2_pipeline') else None
        if aktif_sektor and aktif_sektor == sektor and res.confidence_score >= 0.90:
            # Generic follow-up kontrolü
            generic_patterns = [
                r"\b(fiyat|ücret|maliyet|teklif|referans|süre|kurulum)\b",
                r"\b(hangi|nasıl|ne kadar|nedir|bilgi|liste|listeler|kiminle|kimlerle)\b",
                r"\b(price|cost|quote|pricing|how long|how much|information|list|references|who|contact)\b"
            ]
            is_generic = any(re.search(pattern, kullanici_girdisi.lower()) for pattern in generic_patterns)
            if is_generic:
                yontem = "hafiza"
                mod = "HAFIZA"

        top_candidates = []
        if res.top_candidates:
            top_candidates = res.top_candidates

        return ChatbotResponse(
            girdi=kullanici_girdisi,
            normalize_girdi=res.preprocessed_query if res.preprocessed_query else res.query,
            sektor=sektor,
            mod=mod,
            skor=res.confidence_score,
            yontem=yontem,
            lang="tr",
            eslesen_mesaj="",
            eslesen_id=None,
            aciklama=f"Pipeline run layer={res.layer}",
            temiz_sorgu=res.query,
            rewrite_backend="simulated",
            negated_sectors=res.negated_sectors,
            masked_sectors=[],
            inspector_label=sektor,
            k1_hints={},
            yanit_mesaji=res.response_message,
            top_candidates=top_candidates
        )

        # ------------------------------------------------------------------
        # 3) Jenerik takip + aktif_sektor → HAFIZA
        # ------------------------------------------------------------------
        if aktif and is_generic_followup(kullanici_girdisi):
            return self._yanit_hafiza(
                kullanici_girdisi=kullanici_girdisi,
                normalize_girdi=used_query,
                sektor=aktif,
                lang=lang,
                clean=clean,
                rewrite_backend=rewritten.backend,
                bge_skor=skor,
            )

        # ------------------------------------------------------------------
        # 4) Fallback
        # ------------------------------------------------------------------
        return self._fallback_belirsiz(
            kullanici_girdisi=kullanici_girdisi,
            normalize_girdi=used_query,
            lang=lang,
            clean=clean,
            rewrite_backend=rewritten.backend,
            skor=skor,
            eslesen_mesaj=best.text or "",
            eslesen_id=(best.metadata or {}).get("id"),
            aciklama=(
                f"BGE-first | query={used_query!r} | "
                f"en iyi BGE({sektor})={skor:.3f} < {self.MIN_BGE} → "
                f"fallback güvenlik ağı"
            ),
            top_candidates=self._hits_to_top_candidates(top_results),
        )


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bot = Chatbot()
    print(
        f"Corpus: {bot.corpus_boyutu()} | BGE: "
        f"{'aktif' if bot.bge_aktif_mi() else 'yok'} | MIN_BGE={bot.MIN_BGE}"
    )
    print("Akis: K1(kisaltma) / K2(BGE) -> (jenerik+hafiza) HAFIZA -> FB")
    sid = "demo-session"
    for q in (
        "Hastane yönetim sistemi arıyoruz",
        "demo istiyorum",
        "fiyat teklifi almak istiyorum",
        "LMS kurulumu icin teklif",
        "bilgi alabilir miyim",
    ):
        y = bot.sor(q, session_id=sid)
        print(
            f"[{y.mod}/{y.sektor}] skor={y.skor:.3f} {y.yontem} "
            f"hafiza={bot.get_aktif_sektor(sid)!r} ← {q!r}"
        )
