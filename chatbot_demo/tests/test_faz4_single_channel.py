"""FAZ 4 — tek kanal Top-3 + latency alanları."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import ChatbotResponse
from src.chitchat_rules import FastPathHit, MSG_GREETING
from src.frontend import FAST_PATH_NOTICE, serialize_fast_path, serialize_response
from src.intent_router_contract import apply_smart_rerank_to_candidates


def test_serialize_fast_path_latency_and_notice():
    hit = FastPathHit(
        category="greeting",
        sub_intent="chitchat.greeting",
        status="SUCCESS",
        response_message=MSG_GREETING,
    )
    p = serialize_fast_path(
        "Merhaba",
        hit,
        sure_ms=1.2,
        execution_time_ms=1.2,
        total_latency_ms=1.2,
    )
    assert p["fast_path_notice"] == FAST_PATH_NOTICE
    assert p["execution_time_ms"] == 1.2
    assert p["total_latency_ms"] == 1.2
    assert p["sure_ms"] == 1.2
    assert p["top_candidates"] == []
    assert p["intent_router"]["top_candidates"] == []


def test_serialize_uses_precomputed_candidates_not_second_bge(monkeypatch):
    """Önceden bağlı Top-3 kullanılmalı — collect_debug çağrılmamalı."""
    import src.frontend as fe
    import src.intent_router_contract as irc

    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise AssertionError("ikinci retrieval olmamalı")

    monkeypatch.setattr(irc, "collect_debug_candidates", boom)

    pre = [
        {
            "text": "Kardiyoloji randevusu",
            "sector": "health",
            "sub_intent": "health.appointment",
            "initial_score": 0.91,
            "reranker_score": None,
        }
    ]
    resp = ChatbotResponse(
        girdi="Kardiyoloji randevusu",
        normalize_girdi="kardiyoloji randevusu",
        sektor="sağlık",
        mod="K2",
        skor=0.91,
        yontem="bge-m3",
        temiz_sorgu="Kardiyoloji randevusu",
        top_candidates=pre,
    )

    def fake_smart(q, cands):
        out = [dict(c) for c in cands]
        for c in out:
            c["reranker_score"] = c["initial_score"]
        return out

    monkeypatch.setattr(irc, "apply_smart_rerank_to_candidates", fake_smart)
    # frontend imports inside function — patch module used by serialize
    monkeypatch.setattr(
        "src.intent_router_contract.collect_debug_candidates",
        boom,
    )
    monkeypatch.setattr(
        "src.intent_router_contract.apply_smart_rerank_to_candidates",
        fake_smart,
    )

    p = serialize_response(resp, sure_ms=12.0, execution_time_ms=10.0, total_latency_ms=12.0)
    assert calls["n"] == 0
    assert p["top_candidates"][0]["sector"] == "health"
    assert p["intent_router"]["top_candidates"][0]["text"] == "Kardiyoloji randevusu"
    assert p["top_candidates"] is not None
    assert p["execution_time_ms"] == 10.0
    assert p["total_latency_ms"] == 12.0


def test_k1_serialize_shows_fast_path_notice():
    resp = ChatbotResponse(
        girdi="hbys",
        normalize_girdi="hbys",
        sektor="sağlık",
        mod="K1",
        skor=1.0,
        yontem="kisaltma",
        temiz_sorgu="hbys",
        top_candidates=[],
    )
    p = serialize_response(resp, total_latency_ms=0.5, execution_time_ms=0.4)
    assert p["fast_path_notice"] == FAST_PATH_NOTICE
    assert p["top_candidates"] == []
    assert p["mod"] == "K1"


def test_smart_rerank_mirrors_bge_no_ce():
    """Reranker kaldırıldı — final_score/reranker_score her zaman initial_score'u yansıtır."""
    cands = [
        {
            "text": "a",
            "sector": "health",
            "sub_intent": "health.general",
            "initial_score": 0.90,
            "reranker_score": None,
        }
    ]
    out = apply_smart_rerank_to_candidates("q", cands)
    assert out[0]["reranker_score"] == 0.90
    assert out[0]["final_score"] == 0.90
