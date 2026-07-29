"""FAZ 5 — BGE-M3 strict gate (reranker/fusion kaldırıldı), kavram genişletme, unresolved logger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.concept_map import expand_query_concept_seeds, expand_query_concepts
from src.intent_router_contract import apply_rerank_decision, apply_smart_rerank_to_candidates
from src.k1_guardrails import DECISION_THRESHOLD
from src.unresolved_logger import log_unresolved_query
from src.chatbot import ChatbotResponse


def test_decision_threshold_is_065():
    assert abs(DECISION_THRESHOLD - 0.65) < 1e-9


def test_strict_gate_promotes_high_bge_no_ce():
    """Reranker/Fusion kaldırıldı: BGE tek başına >= 0.65 ise K2."""
    resp = ChatbotResponse(
        girdi="q",
        normalize_girdi="q",
        sektor="belirsiz",
        mod="FB",
        skor=0.79,
        yontem="fb",
    )
    cands = [
        {
            "text": "randevu",
            "sector": "saglik",
            "sub_intent": "saglik.randevu",
            "initial_score": 0.79,
            "reranker_score": 0.79,
            "final_score": 0.79,
        }
    ]
    out, _ = apply_rerank_decision(resp, cands)
    assert out.mod == "K2"
    assert out.sektor == "saglik"
    assert out.skor >= DECISION_THRESHOLD


def test_concept_expansion_psikolog_and_muze():
    seeds = expand_query_concept_seeds("Sınav stresi için psikolog")
    assert seeds
    joined = " ".join(seeds).lower()
    assert "psikolog" in joined or "psikoloji" in joined

    # Sınav/sinav testini health priority olmayan ayrı bir sorgu ile yapıyoruz
    seeds_edu = expand_query_concept_seeds("Sınav burs başvurusu")
    assert seeds_edu
    joined_edu = " ".join(seeds_edu).lower()
    assert "sınav" in joined_edu or "sinav" in joined_edu.replace("ı", "i")

    one = expand_query_concepts("Müze kart fiyatı")
    assert one is not None
    assert "müze" in one.lower() or "muze" in one.lower().replace("ü", "u")


def test_unresolved_logger_writes_json(tmp_path: Path):
    log_path = tmp_path / "unresolved_queries.json"
    log_unresolved_query(
        "belirsiz deneme",
        top_candidates=[
            {
                "text": "x",
                "sector": "saglik",
                "sub_intent": "saglik.genel",
                "initial_score": 0.55,
                "reranker_score": 0.02,
                "final_score": 0.232,
            }
        ],
        skor=0.55,
        mod="FB",
        path=log_path,
    )
    rows = json.loads(log_path.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["query"] == "belirsiz deneme"
    assert rows[0]["top_candidates"][0]["initial_score"] == 0.55


def test_smart_rerank_sets_final_score():
    """Reranker kaldırıldı — final_score/reranker_score BGE'yi (initial_score) yansıtır."""
    cands = [
        {
            "text": "a",
            "sector": "saglik",
            "sub_intent": "saglik.genel",
            "initial_score": 0.70,
            "reranker_score": None,
        }
    ]
    out = apply_smart_rerank_to_candidates("q", cands)
    assert out[0]["reranker_score"] == 0.70
    assert abs(out[0]["final_score"] - 0.70) < 1e-3
