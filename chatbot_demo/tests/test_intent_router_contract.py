"""Intent Router JSON adaptörü — ChatbotResponse alanlarını bozmadan spec çıktısı."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import ChatbotResponse, MIN_BGE
from src.intent_router_contract import (
    map_sector,
    map_status,
    map_sub_intent,
    to_intent_router_json,
)


def _resp(**kwargs) -> ChatbotResponse:
    base = dict(
        girdi="test",
        normalize_girdi="test",
        sektor="sağlık",
        mod="K2",
        skor=0.9,
        yontem="bge-m3",
    )
    base.update(kwargs)
    return ChatbotResponse(**base)


def test_map_sector_tr_to_en():
    assert map_sector("sağlık") == "saglik"
    assert map_sector("turizm") == "turizm"
    assert map_sector("savunma") == "ood"
    assert map_sector("eğitim") == "egitim"
    assert map_sector("belirsiz") == "ood"


def test_sub_intent_keyword_health_appointment():
    assert map_sub_intent("saglik", "Kardiyoloji randevusu almak istiyorum") == (
        "saglik.randevu"
    )


def test_sub_intent_default_general():
    assert map_sub_intent("saglik", "sağlık sistemi hakkında bilgi") == "saglik.genel"


def test_sub_intent_from_seed_code():
    assert (
        map_sub_intent("turizm", "bir şey", seed_intent_code="tourism_hotel")
        == "turizm.otel"
    )


def test_status_success_above_min_bge():
    r = _resp(mod="K2", skor=0.85, sektor="sağlık")
    assert map_status(r, "saglik", 0.85) == "SUCCESS"
    assert 0.85 >= MIN_BGE


def test_status_uncertain_fallback_below_threshold():
    # FB her zaman sektor=belirsiz → map_sector=ood; mid skor → UNCERTAIN
    r = _resp(mod="FB", skor=0.62, sektor="belirsiz", yontem="fb")
    assert map_status(r, "ood", 0.62) == "UNCERTAIN"
    r2 = _resp(mod="FB", skor=0.62, sektor="sağlık", yontem="fb")
    assert map_status(r2, "saglik", 0.62) == "UNCERTAIN"


def test_status_uncertain_high_score_margin_fb():
    r = _resp(mod="FB", skor=0.88, sektor="sağlık", yontem="fb")
    assert map_status(r, "saglik", 0.88) == "UNCERTAIN"


def test_status_ood_low_signal():
    r = _resp(mod="FB", skor=0.12, sektor="belirsiz", yontem="fb")
    assert map_status(r, "ood", 0.12) == "OOD"


def test_full_contract_payload_shape():
    r = _resp(
        girdi="Kardiyoloji randevusu almak istiyorum",
        sektor="sağlık",
        mod="K2",
        skor=0.91,
    )
    payload = to_intent_router_json(r, latency_ms=112)
    assert payload["status"] == "SUCCESS"
    assert payload["intent"]["sector"] == "saglik"
    assert payload["intent"]["sub_intent"] == "saglik.randevu"
    assert payload["intent"]["confidence_score"] == 0.91
    assert payload["latency_ms"] == 112
    assert "sağlık" in payload["response_message"].lower() or "yönlendir" in payload["response_message"].lower()
    assert payload["redirect_url"] == "/saglik"
    assert "top_candidates" not in payload


def test_contract_with_top_candidates():
    r = _resp(girdi="otel", sektor="turizm", mod="K2", skor=0.9)
    cands = [
        {
            "text": "otel",
            "sector": "turizm",
            "sub_intent": "turizm.otel",
            "initial_score": 0.9,
            "reranker_score": 0.85,
        },
    ]
    payload = to_intent_router_json(
        r, latency_ms=50, top_candidates=cands, include_top_candidates=True
    )
    assert payload["top_candidates"] == cands
    assert payload["redirect_url"] == "/turizm"


def test_ood_forces_sector_and_sub():
    r = _resp(
        girdi="bugün hava çok güzel",
        sektor="belirsiz",
        mod="FB",
        skor=0.05,
        yontem="fb",
    )
    payload = to_intent_router_json(r, latency_ms=40)
    assert payload["status"] == "OOD"
    assert payload["intent"]["sector"] == "ood"
    assert payload["intent"]["sub_intent"] == "ood.none"
    assert payload["redirect_url"] == ""
    msg = payload["response_message"].lower()
    assert "yardımcı olamıyorum" in msg or "sağlık" in msg

def test_chatbot_response_fields_unchanged():
    """Mevcut UI/test sözleşmesi: sektor/mod/skor/yontem korunur."""
    r = _resp()
    assert r.sektor == "sağlık"
    assert r.mod == "K2"
    assert r.skor == 0.9
    assert "intent" in r.to_intent_router(latency_ms=10)
    assert "response_message" in r.to_intent_router(latency_ms=10)
    assert r.to_intent_router(latency_ms=10)["redirect_url"] == "/saglik"
