"""
Intent Router → Frontend metadata sözleşmesi.

demo/server.py ve diğer UI katmanları ChatbotResponse'u bu helper ile JSON'a çevirir.
Tek kanal: BGE Top-3 ChatbotResponse'tan gelir; ikinci retrieval yok.
ML karar = BGE-M3 raw cosine (Top-1 ≥ 0.65; K1/HAFIZA korunur). Reranker YOK.
"""
from __future__ import annotations

from typing import Any

from src.chatbot import ChatbotResponse
from src.chitchat_rules import FastPathHit

INSPECTOR_DEMO_SCENARIO = (
    "Sağlık/hastane değil! Lojistik kargo rotalarımızı optimize etmemiz lazım."
)

FAST_PATH_NOTICE = "Katman 1 Kısayolu Çalıştı (Fast-Path)"


def _attach_latency(
    payload: dict[str, Any],
    *,
    execution_time_ms: float | None,
    total_latency_ms: float | None,
    sure_ms: float | None,
) -> dict[str, Any]:
    exec_v = execution_time_ms if execution_time_ms is not None else sure_ms
    total_v = total_latency_ms if total_latency_ms is not None else sure_ms
    if exec_v is not None:
        payload["execution_time_ms"] = round(float(exec_v), 2)
    if total_v is not None:
        payload["total_latency_ms"] = round(float(total_v), 2)
        payload["sure_ms"] = round(float(total_v), 2)
    elif sure_ms is not None:
        payload["sure_ms"] = round(float(sure_ms), 2)
    # Contract latency = total (UI wall-clock ile hizalı)
    if "intent_router" in payload and isinstance(payload["intent_router"], dict):
        lat = total_v if total_v is not None else sure_ms
        if lat is not None:
            payload["intent_router"]["latency_ms"] = int(round(float(lat)))
    return payload


def serialize_fast_path(
    message: str,
    hit: FastPathHit,
    sure_ms: float | None = None,
    *,
    execution_time_ms: float | None = None,
    total_latency_ms: float | None = None,
) -> dict[str, Any]:
    """Katman-1 chitchat/gibberish/abuse — model yok, Top-3 yok."""
    lat = total_latency_ms if total_latency_ms is not None else sure_ms
    router = {
        "query": message,
        "intent": {
            "sector": "ood",
            "sub_intent": hit.sub_intent,
            "confidence_score": round(float(hit.confidence_score), 4),
        },
        "status": hit.status,
        "latency_ms": int(round(lat or 0)),
        "response_message": hit.response_message,
        "redirect_url": "",
        "top_candidates": [],
    }
    label_map = {
        "greeting": "Selamlama",
        "thanks": "Teşekkür",
        "identity": "Asistan",
        "gibberish": "Anlaşılamadı",
        "abuse": "Uygunsuz içerik",
    }
    label = label_map.get(hit.category, "Hızlı yanıt")
    payload: dict[str, Any] = {
        "sektor": "belirsiz",
        "mod": "RULE",
        "skor": round(float(hit.confidence_score), 4),
        "guven_skoru": round(float(hit.confidence_score), 4),
        "yontem": "rule",
        "lang": "tr",
        "aciklama": f"Katman-1 fast-path | {hit.category}",
        "yanit_mesaji": hit.response_message,
        "temiz_sorgu": message,
        "clean_query": message,
        "rewrite_backend": "none",
        "normalize_girdi": message,
        "negated_sectors": [],
        "masked_sectors": [],
        "k1_hints": {},
        "inspector_label": label,
        "fast_path_notice": FAST_PATH_NOTICE,
        "metadata": {
            "clean_query": message,
            "confidence": round(float(hit.confidence_score), 4),
            "masked_sectors": [],
            "negated_sectors": [],
            "sektor": "belirsiz",
            "mod": "RULE",
            "k1_hints": {},
            "layer": "rule",
            "category": hit.category,
            "fast_path_notice": FAST_PATH_NOTICE,
        },
        "show_inspector": True,
        "eslesen_mesaj": "",
        "eslesen_id": None,
        "pipeline": "Katman-1 Rule → (ML atlandı)",
        "confidence_band": "singularity",
        "inspector_demo_scenario": INSPECTOR_DEMO_SCENARIO,
        "intent_router": router,
        "response_message": hit.response_message,
        "redirect_url": "",
        "top_candidates": [],
        "layer": "rule",
    }
    return _attach_latency(
        payload,
        execution_time_ms=execution_time_ms if execution_time_ms is not None else lat,
        total_latency_ms=lat,
        sure_ms=sure_ms,
    )


def serialize_response(
    resp: ChatbotResponse,
    sure_ms: float | None = None,
    *,
    include_top_candidates: bool = True,
    execution_time_ms: float | None = None,
    total_latency_ms: float | None = None,
) -> dict[str, Any]:
    """ChatbotResponse → Intent Router UI metadata (JSON-safe). Tek kanal Top-3."""
    from src.intent_router_contract import (
        apply_rerank_decision,
        apply_smart_rerank_to_candidates,
        collect_debug_candidates,
    )

    clean = getattr(resp, "temiz_sorgu", "") or ""
    masked = list(getattr(resp, "masked_sectors", None) or [])
    negated = list(getattr(resp, "negated_sectors", None) or [])
    k1_hints = getattr(resp, "k1_hints", None) or {}
    is_k1 = (resp.mod or "").upper() == "K1"
    is_hafiza = (resp.mod or "").upper() == "HAFIZA"

    top_candidates: list[dict[str, Any]] = []
    if include_top_candidates and not is_k1 and not is_hafiza:
        precomputed = list(getattr(resp, "top_candidates", None) or [])
        if precomputed:
            top_candidates = apply_smart_rerank_to_candidates(
                resp.girdi or clean,
                precomputed,
            )
        else:
            try:
                top_candidates = collect_debug_candidates(
                    resp.girdi or clean,
                    top_k=3,
                )
            except Exception:
                top_candidates = []

    # ML otoritesi: BGE-M3 raw Top-1 (K1/K2/HAFIZA dokunulmaz)
    if (resp.mod or "").upper() in ("K1", "K2", "HAFIZA"):
        eff = resp
    else:
        eff, top_candidates = apply_rerank_decision(resp, top_candidates)

    skor = round(float(eff.skor), 4)
    label = getattr(eff, "inspector_label", "") or ""
    if not label:
        if eff.mod == "FB":
            label = "Genel Sohbet" if getattr(eff, "yontem", "") == "small_talk" else "Sektör Belirsiz"
        elif eff.mod == "HAFIZA":
            label = f"Hafıza · {eff.sektor}"
        else:
            label = eff.sektor

    fast_notice = FAST_PATH_NOTICE if is_k1 else ""

    show_inspector = (
        getattr(eff, "yontem", "") != "small_talk"
        and bool(clean.strip())
        and (
            (eff.mod != "FB" and eff.sektor not in ("", "belirsiz"))
            or bool(k1_hints)
            or bool(top_candidates)
            or is_k1
        )
    )

    metadata: dict[str, Any] = {
        "clean_query": clean,
        "confidence": skor,
        "masked_sectors": masked,
        "negated_sectors": negated,
        "sektor": eff.sektor,
        "mod": eff.mod,
        "k1_hints": k1_hints,
    }
    if fast_notice:
        metadata["fast_path_notice"] = fast_notice

    lat = total_latency_ms if total_latency_ms is not None else sure_ms
    router = eff.to_intent_router(
        latency_ms=lat,
        top_candidates=top_candidates,
        include_top_candidates=include_top_candidates,
    )

    yanit = getattr(eff, "yanit_mesaji", "") or ""
    if not yanit:
        yanit = router.get("response_message", "") or ""

    # Inspector ↔ karar: aynı liste referansı
    synced = list(router.get("top_candidates") or top_candidates)

    payload: dict[str, Any] = {
        "sektor": eff.sektor,
        "mod": eff.mod,
        "skor": skor,
        "guven_skoru": skor,
        "yontem": eff.yontem,
        "lang": getattr(eff, "lang", "tr"),
        "aciklama": eff.aciklama,
        "yanit_mesaji": yanit,
        "temiz_sorgu": clean,
        "clean_query": clean,
        "rewrite_backend": getattr(eff, "rewrite_backend", "") or "",
        "normalize_girdi": getattr(eff, "normalize_girdi", "") or "",
        "negated_sectors": negated,
        "masked_sectors": masked,
        "k1_hints": k1_hints,
        "inspector_label": label,
        "metadata": metadata if show_inspector else {},
        "show_inspector": show_inspector or bool(synced) or is_k1,
        "eslesen_mesaj": (eff.eslesen_mesaj[:80] if eff.eslesen_mesaj else ""),
        "eslesen_id": eff.eslesen_id,
        "pipeline": (
            "User → LLMRewriter → K1(kısaltma) → "
            "K2(tek-kanal BGE-M3 raw ≥0.65) → HAFIZA → FB"
        ),
        "confidence_band": _confidence_band(skor),
        "inspector_demo_scenario": INSPECTOR_DEMO_SCENARIO,
        "intent_router": router,
        "response_message": router.get("response_message", "") or yanit,
        "redirect_url": router.get("redirect_url", ""),
        "top_candidates": synced,
    }
    if fast_notice:
        payload["fast_path_notice"] = fast_notice

    return _attach_latency(
        payload,
        execution_time_ms=execution_time_ms,
        total_latency_ms=lat,
        sure_ms=sure_ms,
    )


def _confidence_band(skor: float) -> str:
    if skor < 0.85:
        return "fallback"
    if skor >= 0.92:
        return "singularity"
    return "mid"
