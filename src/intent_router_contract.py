"""
Intent Router JSON sözleşmesi — mevcut ChatbotResponse üzerine adaptör.

{
  "query": "...",
  "intent": {
    "sector": "health|tourism|defense|education|ood",
    "sub_intent": "health.appointment",
    "confidence_score": 0.85
  },
  "status": "SUCCESS|UNCERTAIN|OOD",
  "latency_ms": 112,
  "response_message": "...",
  "redirect_url": "/health",
  "top_candidates": [   // isteğe bağlı (debug / demo Top-3)
    {
      "text": "...",
      "sector": "health",
      "sub_intent": "health.appointment",
      "initial_score": 0.91,
      "reranker_score": 0.88
    }
  ]
}
"""

from __future__ import annotations

from typing import Any

from src.chatbot import MIN_BGE, ChatbotResponse, to_ascii, _normalize

# TR sektör → spec sector
SECTOR_MAP: dict[str, str] = {
    "sağlık": "saglik",
    "saglik": "saglik",
    "health": "saglik",
    "turizm": "turizm",
    "tourism": "turizm",
    "eğitim": "egitim",
    "egitim": "egitim",
    "education": "egitim",
    "bilişim": "bilisim",
    "bilisim": "bilisim",
    "it": "bilisim",
    "software": "bilisim",
    "eğlence": "eglence",
    "eglence": "eglence",
    "entertainment": "eglence",
    "belirsiz": "ood",
    "": "ood",
    "?": "ood",
}

_SEED_TO_SUB: dict[str, str] = {
    "health_appointment":     "saglik.randevu",
    "tourism_hotel":          "turizm.otel",
    "education_enrollment":   "egitim.kayit",
    "bilisim_integration":    "bilisim.entegrasyon",
    "eglence_streaming":      "eglence.yayin",
    "defense_communications": "savunma.haberlesme",
    "sector_form_request":    "ood.form",
    "ood":                    "ood.none",
}

_DEFAULT_SUB: dict[str, str] = {
    "saglik":  "saglik.genel",
    "turizm":  "turizm.genel",
    "egitim":  "egitim.genel",
    "bilisim": "bilisim.genel",
    "eglence": "eglence.genel",
    "savunma": "savunma.genel",
    "ood":     "ood.none",
}

_SUB_RULES: dict[str, list[tuple[str, str]]] = {
    "saglik": [
        ("randevu", "saglik.randevu"),
        ("poliklinik", "saglik.randevu"),
        ("hbys", "saglik.hbys"),
        ("enabiz", "saglik.ehr"),
        ("ahbs", "saglik.ehr"),
        ("tahlil", "saglik.lab"),
        ("lab", "saglik.lab"),
        ("hastane", "saglik.hospital"),
        ("klinik", "saglik.clinic"),
    ],
    "turizm": [
        ("rezervasyon", "turizm.reservation"),
        ("otel", "turizm.hotel"),
        ("konaklama", "turizm.hotel"),
        ("pnr", "turizm.booking"),
        ("bilet", "turizm.ticket"),
        ("muze", "turizm.museum"),
        ("checkin", "turizm.checkin"),
        ("check-in", "turizm.checkin"),
    ],
    "egitim": [
        ("lms", "egitim.lms"),
        ("obs", "egitim.sis"),
        ("obys", "egitim.sis"),
        ("transkript", "egitim.transcript"),
        ("kayit", "egitim.enrollment"),
        ("harc", "egitim.tuition"),
        ("cift anadal", "egitim.double_major"),
        ("yaz okulu", "egitim.summer_school"),
    ],
    "bilisim": [
        ("api", "bilisim.api"),
        ("sdk", "bilisim.sdk"),
        ("saas", "bilisim.saas"),
        ("bulut", "bilisim.cloud"),
        ("cloud", "bilisim.cloud"),
        ("entegrasyon", "bilisim.integration"),
        ("yazilim", "bilisim.software"),
        ("yazılım", "bilisim.software"),
        ("otomasyon", "bilisim.automation"),
        ("crm", "bilisim.crm"),
        ("erp", "bilisim.erp"),
        ("siber", "bilisim.security"),
    ],
    "eglence": [
        ("ott", "eglence.streaming"),
        ("streaming", "eglence.streaming"),
        ("yayin", "eglence.streaming"),
        ("oyun", "eglence.game"),
        ("render", "eglence.render"),
        ("metacast", "eglence.media"),
    ],
}

# ---------------------------------------------------------------------------
# Sektör → redirect_url + response_message (config)
# ---------------------------------------------------------------------------
SECTOR_REDIRECT: dict[str, str] = {
    "saglik": "/saglik",
    "turizm": "/turizm",
    "egitim": "/egitim",
    "bilisim": "/bilisim",
    "eglence": "/eglence",
    "ood": "",
}

_SECTOR_TR: dict[str, str] = {
    "saglik": "saglik",
    "turizm": "turizm",
    "egitim": "egitim",
    "bilisim": "bilisim",
    "eglence": "eglence",
}

SECTOR_RESPONSE: dict[str, dict[str, str]] = {
    "saglik": {
        "redirect_url": "/saglik",
        "response_message": (
            "Sağlık hizmetleri ve randevu işlemleriniz için "
            "ilgili sayfaya yönlendiriliyorsunuz..."
        ),
    },
    "turizm": {
        "redirect_url": "/turizm",
        "response_message": (
            "Turizm ve konaklama işlemleriniz için "
            "ilgili sayfaya yönlendiriliyorsunuz..."
        ),
    },
    "egitim": {
        "redirect_url": "/egitim",
        "response_message": (
            "Eğitim ve öğrenci işlemleriniz için "
            "ilgili sayfaya yönlendiriliyorsunuz..."
        ),
    },
    "bilisim": {
        "redirect_url": "/bilisim",
        "response_message": (
            "Bilişim ve yazılım süreçleriniz için "
            "ilgili sayfaya yönlendiriliyorsunuz..."
        ),
    },
    "eglence": {
        "redirect_url": "/eglence",
        "response_message": (
            "Eğlence ve medya hizmetleriniz için "
            "ilgili sayfaya yönlendiriliyorsunuz..."
        ),
    },
    "ood": {
        "redirect_url": "",
        "response_message": (
            "Bu konuda size doğrudan yardımcı olamıyorum. "
            "Size Bilişim, Eğitim, Eğlence, Sağlık veya Turizm alanlarında hizmet verebilirim."
        ),
    },
}

_UNCERTAIN_MSG = (
    "Bu konuda size doğrudan yardımcı olamıyorum. "
    "Size Bilişim, Eğitim, Eğlence, Sağlık veya Turizm alanlarında hizmet verebilirim."
)

_UNCERTAIN_FLOOR = 0.45


def map_sector(sektor_tr: str) -> str:
    key = (sektor_tr or "").strip().lower()
    if key in SECTOR_MAP:
        return SECTOR_MAP[key]
    folded = to_ascii(key).lower()
    return SECTOR_MAP.get(folded, "ood")


def map_sub_intent(sector: str, query: str, *, seed_intent_code: str | None = None) -> str:
    """Geçici mapper — seed intent kodu + anahtar kelime; reranker gelince değişir."""
    if sector == "ood":
        return _DEFAULT_SUB["ood"]

    if seed_intent_code:
        mapped = _SEED_TO_SUB.get(seed_intent_code.strip().lower())
        if mapped and mapped.startswith(f"{sector}."):
            return mapped

    q = to_ascii(_normalize(query or "")).lower()
    for needle, label in _SUB_RULES.get(sector, []):
        if needle in q:
            return label
    return _DEFAULT_SUB.get(sector, f"{sector}.general")


def map_status(resp: ChatbotResponse, sector: str, confidence: float) -> str:
    from src.k1_guardrails import DECISION_THRESHOLD
    mod = (resp.mod or "").upper()
    if sector != "ood" and mod in ("K1", "K2", "HAFIZA"):
        return "SUCCESS"
    if mod == "FB" and confidence >= float(DECISION_THRESHOLD):
        return "UNCERTAIN"
    if mod == "FB" and _UNCERTAIN_FLOOR <= confidence < float(DECISION_THRESHOLD):
        return "UNCERTAIN"
    return "OOD"


def resolve_redirect_url(sector: str, sub_intent: str, status: str) -> str:
    """Sektör → /health|/tourism|/defense|/education (yalnızca SUCCESS)."""
    if status != "SUCCESS" or sector == "ood":
        return ""
    cfg = SECTOR_RESPONSE.get(sector) or {}
    return cfg.get("redirect_url") or SECTOR_REDIRECT.get(sector, "")


def resolve_response_message(
    sector: str,
    sub_intent: str,
    status: str,
    *,
    redirect_url: str | None = None,
) -> str:
    """Kullanıcıya gösterilecek hazır yanıt metni."""
    if status == "SUCCESS":
        cfg = SECTOR_RESPONSE.get(sector) or {}
        msg = cfg.get("response_message")
        if msg:
            return msg
        tr = _SECTOR_TR.get(sector, sector)
        url = redirect_url if redirect_url is not None else resolve_redirect_url(
            sector, sub_intent, status
        )
        if url:
            return (
                f"Talebinizi {tr} sektörüyle ilişkilendirdim. "
                f"Devam etmek için {url} sayfasına yönlendirilebilirsiniz."
            )
        return f"Talebinizi {tr} sektörüyle ilişkilendirdim."
    if status == "UNCERTAIN":
        return _UNCERTAIN_MSG
    return (SECTOR_RESPONSE.get("ood") or {}).get(
        "response_message",
        "Bu konu şu anki kapsamımız dışında görünüyor.",
    )


def build_top_candidate(
    *,
    sector: str,
    sub_intent: str,
    initial_score: float | None = None,
    reranker_score: float | None = None,
    final_score: float | None = None,
    text: str = "",
) -> dict[str, Any]:
    """Top-3 aday satırı — demo / V2 debug."""
    row: dict[str, Any] = {
        "text": text or "",
        "sector": sector or "ood",
        "sub_intent": sub_intent or "ood.none",
        "initial_score": (
            round(float(initial_score), 4) if initial_score is not None else None
        ),
        "reranker_score": (
            round(float(reranker_score), 4) if reranker_score is not None else None
        ),
    }
    if final_score is not None:
        row["final_score"] = round(float(final_score), 4)
    return row


# Geriye dönük alias
def build_candidate_entry(
    text: str,
    *,
    vector_score: float | None = None,
    reranker_score: float | None = None,
    sector: str = "ood",
    sub_intent: str = "ood.none",
) -> dict[str, Any]:
    return build_top_candidate(
        text=text,
        sector=sector,
        sub_intent=sub_intent,
        initial_score=vector_score,
        reranker_score=reranker_score,
    )


def collect_debug_candidates(
    query: str,
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    V1 demo debug: NPZ hybrid Top-K, BGE-M3 raw cosine (reranker kaldırıldı).
    """
    from src.embedder import get_embedder

    emb = get_embedder()
    hits = emb.find_top_k_hybrid(query, k=top_k, alpha=0.9)
    if not hits:
        return []

    texts = [h.text or "" for h in hits]
    vec_scores = [float(h.score) for h in hits]
    sectors: list[str] = []
    subs: list[str] = []
    for h in hits:
        sector = map_sector(str((h.metadata or {}).get("beklenen_sektor") or ""))
        text = h.text or ""
        sub = map_sub_intent(sector, text) if sector != "ood" else "ood.none"
        sectors.append(sector)
        subs.append(sub)

    cands = [
        build_top_candidate(
            text=texts[i],
            sector=sectors[i],
            sub_intent=subs[i],
            initial_score=vec_scores[i],
            reranker_score=vec_scores[i],
            final_score=vec_scores[i],
        )
        for i in range(len(hits))
    ]
    return sort_candidates_by_rerank(cands)


def apply_smart_rerank_to_candidates(
    query: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Tek kanal: BGE Top-3 raw cosine. Reranker/Fusion kaldırıldı —
    final_score doğrudan initial_score'a eşitlenir.
    """
    del query  # reranker kaldırıldığından artık kullanılmıyor
    cands = [dict(c) for c in (candidates or [])]
    for c in cands:
        bge = float(c.get("initial_score") or 0.0)
        c["reranker_score"] = bge
        c["final_score"] = bge
    return sort_candidates_by_final(cands)


_EN_TO_TR: dict[str, str] = {
    "saglik": "saglik",
    "turizm": "turizm",
    "egitim": "egitim",
    "bilisim": "bilisim",
    "eglence": "eglence",
}

_RERANK_SECTORS = frozenset({"saglik", "turizm", "egitim", "bilisim", "eglence", "savunma"})


def sort_candidates_by_final(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Inspector/karar Top-1 = final_score → rerank → BGE (eksik katman sonda)."""

    def _key(c: dict[str, Any]) -> tuple[int, float]:
        if c.get("final_score") is not None:
            return (0, -float(c["final_score"]))
        if c.get("reranker_score") is not None:
            return (1, -float(c["reranker_score"]))
        if c.get("initial_score") is not None:
            return (2, -float(c["initial_score"]))
        return (3, 0.0)

    return sorted(candidates, key=_key)


def sort_candidates_by_rerank(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Geriye dönük alias — final skor sıralaması."""
    return sort_candidates_by_final(candidates)


def apply_rerank_decision(
    resp: ChatbotResponse,
    top_candidates: list[dict[str, Any]],
    *,
    min_score: float | None = None,
) -> tuple[ChatbotResponse, list[dict[str, Any]]]:
    """
    Demo ML otoritesi: BGE-M3 raw Top-1 ≥ DECISION_THRESHOLD (0.65) → K2.
    K1 / HAFIZA korunur. Skor yoksa V1 kararı aynen kalır.
    Reranker / Soft Fusion kaldırıldı — final_score == initial_score (bge).
    """
    from src.k1_guardrails import DECISION_THRESHOLD

    threshold = float(DECISION_THRESHOLD if min_score is None else min_score)
    ordered = sort_candidates_by_final(list(top_candidates or []))
    mod = (resp.mod or "").upper()
    if mod in ("K1", "HAFIZA"):
        return resp, ordered

    best: dict[str, Any] | None = None
    for c in ordered:
        if c.get("final_score") is not None or c.get("initial_score") is not None:
            best = c
            break
    if best is None:
        return resp, ordered

    bge = float(best.get("initial_score") or 0.0)
    final = float(best["final_score"]) if best.get("final_score") is not None else bge
    sector_en = str(best.get("sector") or "ood")
    sub = str(best.get("sub_intent") or "ood.none")
    text = str(best.get("text") or "")

    if final >= threshold and sector_en in _RERANK_SECTORS:
        sektor_tr = _EN_TO_TR[sector_en]
        msg = resolve_response_message(sector_en, sub, "SUCCESS")
        return (
            ChatbotResponse(
                girdi=resp.girdi,
                normalize_girdi=resp.normalize_girdi,
                sektor=sektor_tr,
                mod="K2",
                skor=final,
                yontem="bge-m3",
                lang=resp.lang,
                eslesen_mesaj=text,
                eslesen_id=resp.eslesen_id,
                aciklama=(
                    f"BGE-M3 gate | Top-1={sector_en}/{sub} | "
                    f"final={final:.3f} (bge={bge:.3f}) "
                    f">= {threshold:.2f} -> K2"
                ),
                temiz_sorgu=resp.temiz_sorgu,
                rewrite_backend=resp.rewrite_backend,
                negated_sectors=list(resp.negated_sectors or []),
                masked_sectors=list(resp.masked_sectors or []),
                inspector_label=sektor_tr,
                k1_hints=dict(resp.k1_hints or {}),
                yanit_mesaji=msg,
                top_candidates=list(ordered),
            ),
            ordered,
        )

    display = max(float(resp.skor or 0.0), final)
    return (
        ChatbotResponse(
            girdi=resp.girdi,
            normalize_girdi=resp.normalize_girdi,
            sektor="belirsiz",
            mod="FB",
            skor=display,
            yontem="fb",
            lang=resp.lang,
            eslesen_mesaj=text,
            eslesen_id=resp.eslesen_id,
            aciklama=(
                f"BGE-M3 gate | Top-1={sector_en} final={final:.3f} "
                f"(bge={bge:.3f}) < {threshold:.2f} -> FB"
            ),
            temiz_sorgu=resp.temiz_sorgu,
            rewrite_backend=resp.rewrite_backend,
            negated_sectors=list(resp.negated_sectors or []),
            masked_sectors=list(resp.masked_sectors or []),
            inspector_label="Sektör Belirsiz",
            k1_hints=dict(resp.k1_hints or {}),
            yanit_mesaji=_UNCERTAIN_MSG,
            top_candidates=list(ordered),
        ),
        ordered,
    )


def to_intent_router_json(
    resp: ChatbotResponse,
    *,
    latency_ms: float | int | None = None,
    seed_intent_code: str | None = None,
    top_candidates: list[dict[str, Any]] | None = None,
    include_top_candidates: bool = False,
    # legacy aliases
    candidates: list[dict[str, Any]] | None = None,
    include_candidates: bool = False,
) -> dict[str, Any]:
    """ChatbotResponse → Intent Router contract."""
    query = resp.girdi or ""
    sector = map_sector(resp.sektor)
    confidence = round(float(resp.skor or 0.0), 4)
    if sector == "ood":
        sub = "ood.none"
    else:
        sub = map_sub_intent(sector, query, seed_intent_code=seed_intent_code)

    status = map_status(resp, sector, confidence)
    if status == "OOD":
        sector = "ood"
        sub = "ood.none"

    redirect_url = resolve_redirect_url(sector, sub, status)
    response_message = resolve_response_message(
        sector, sub, status, redirect_url=redirect_url
    )

    payload: dict[str, Any] = {
        "query": query,
        "intent": {
            "sector": sector,
            "sub_intent": sub,
            "confidence_score": confidence,
        },
        "status": status,
        "latency_ms": int(round(latency_ms)) if latency_ms is not None else 0,
        "response_message": response_message,
        "redirect_url": redirect_url,
    }

    want_cands = include_top_candidates or include_candidates
    cand_list = top_candidates if top_candidates is not None else candidates
    if want_cands:
        payload["top_candidates"] = list(cand_list or [])
    return payload
