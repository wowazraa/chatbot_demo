"""BGE-M3 strict gate (reranker kaldırıldı) + K1 lexicon + typo fold — demo karar hizası."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import (
    ChatbotResponse,
    apply_typo_fold,
    fallback_user_message,
    match_kisaltma,
    to_ascii,
)
from src.intent_router_contract import apply_rerank_decision, sort_candidates_by_rerank


def _resp(**kwargs) -> ChatbotResponse:
    base = dict(
        girdi="q",
        normalize_girdi="q",
        sektor="belirsiz",
        mod="FB",
        skor=0.69,
        yontem="fb",
    )
    base.update(kwargs)
    return ChatbotResponse(**base)


def test_sort_candidates_by_rerank():
    cands = [
        {"text": "a", "sector": "saglik", "sub_intent": "saglik.genel", "initial_score": 0.9, "reranker_score": 0.2},
        {"text": "b", "sector": "saglik", "sub_intent": "saglik.randevu", "initial_score": 0.7, "reranker_score": 0.91},
        {"text": "c", "sector": "ood", "sub_intent": "ood.none", "initial_score": 0.5, "reranker_score": None},
    ]
    ordered = sort_candidates_by_rerank(cands)
    assert ordered[0]["text"] == "b"
    assert ordered[0]["reranker_score"] == 0.91
    assert ordered[-1]["reranker_score"] is None


def test_rerank_gate_promotes_fb_to_k2():
    resp = _resp(mod="FB", skor=0.69, sektor="belirsiz")
    cands = [
        {
            "text": "online randevu",
            "sector": "saglik",
            "sub_intent": "saglik.randevu",
            "initial_score": 0.68,
            "reranker_score": 0.68,
        }
    ]
    # Reranker kaldırıldı: final == bge == 0.68 >= strict 0.65 gate → K2
    out, ordered = apply_rerank_decision(resp, cands)
    assert out.mod == "K2"
    assert out.sektor == "saglik"
    assert abs(out.skor - 0.68) < 1e-3
    assert out.yontem == "bge-m3"
    assert "/saglik" in (out.yanit_mesaji or "") or "saglik" in to_ascii(out.yanit_mesaji or "").lower()
    assert ordered[0]["reranker_score"] == 0.68


def test_rerank_gate_rejects_below_threshold():
    resp = _resp(mod="K2", skor=0.85, sektor="saglik")
    cands = [
        {
            "text": "zayıf eşleşme",
            "sector": "saglik",
            "sub_intent": "saglik.randevu",
            "initial_score": 0.60,
            "reranker_score": 0.60,
        }
    ]
    # final == bge == 0.60 < strict 0.65 gate → FB; display = max(0.85, 0.60)
    out, _ = apply_rerank_decision(resp, cands)
    assert out.mod == "FB"
    assert out.sektor == "belirsiz"
    assert abs(out.skor - max(0.85, 0.60)) < 1e-3
    assert "yardımcı olamıyorum" in (out.yanit_mesaji or "").lower()


def test_rerank_gate_preserves_k1():
    resp = _resp(mod="K1", skor=1.0, sektor="turizm", yontem="kisaltma")
    cands = [
        {
            "text": "otel",
            "sector": "turizm",
            "sub_intent": "turizm.otel",
            "initial_score": 0.5,
            "reranker_score": 0.5,
        }
    ]
    out, _ = apply_rerank_decision(resp, cands)
    assert out.mod == "K1"
    assert out.sektor == "turizm"
    assert out.skor == 1.0


def test_rerank_gate_noop_without_scores():
    resp = _resp(mod="K2", skor=0.85, sektor="saglik", yontem="bge-m3")
    cands = [
        {
            "text": "x",
            "sector": "saglik",
            "sub_intent": "saglik.genel",
            "initial_score": 0.85,
            "reranker_score": 0.85,
        }
    ]
    out, _ = apply_rerank_decision(resp, cands)
    assert out.mod == "K2"
    assert out.skor == 0.85


def test_k1_only_institutional_abbreviations():
    # Jenerik kelimeler / uzun cümleler → K1 yok (ML)
    assert match_kisaltma("hastane randevu sistemine nasıl girerim") is None
    assert match_kisaltma("sınır güvenliği radar sistemleri") is None
    assert match_kisaltma("yazılım mühendisliği burs imkanları") is None
    assert match_kisaltma("Bilgisayar mühendisliği taban puanları ve burs imkanları") is None
    assert match_kisaltma("Ege bölgesindeki her şey dahil otel fiyatları") is None
    # Net kurumsal kısaltma (kısa) → K1
    assert match_kisaltma("hbys")[0] == "saglik"
    assert match_kisaltma("obs lms kuracağız")[0] == "egitim"
    assert match_kisaltma("pnr sorgula")[0] == "turizm"


def test_typo_fold_randvu():
    assert "randevu" in apply_typo_fold("hastaneden randvu alıcaktm")
    # Typo düzelince de K1 yok — semantik ML yolu
    assert match_kisaltma(apply_typo_fold("hastaneden randvu alıcaktm yardm")) is None


def test_fallback_no_greeting_on_contentful_selamlar():
    msg = fallback_user_message(
        "Selamlar iyi çalışmalar, hastane randevu sistemine nasıl girerim?"
    )
    assert "Merhaba!" not in msg
    assert "net anlayamadım" in msg.lower() or "sektör" in msg.lower()


def test_education_taban_burs_via_ml_not_k1():
    """FAZ 2: akademik sorgu K1'e takılmaz; B2C olduğundan ood/belirsiz."""
    from src.chatbot import Chatbot, MIN_BGE
    from src.embedder import reset_embedder

    q = "Bilgisayar mühendisliği taban puanları ve burs imkanları"
    assert match_kisaltma(q) is None

    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    resp = bot.sor(q)
    assert resp.mod == "FB"
    assert resp.sektor == "belirsiz"


def test_english_routing():
    """English query routing, noise removal, and intent_router serialization checks."""
    from src.v2_pipeline import V2IntentPipeline
    
    pipe = V2IntentPipeline()
    q = "Hi there, looking for shift scheduling software for 200 warehouse staff."
    res = pipe.run(q)
    
    assert res.detected_language == "en"
    assert "looking for" not in res.processed_intent.lower()
    assert "hi there" not in res.processed_intent.lower()
    
    payload = res.to_intent_router()
    assert payload["detected_language"] == "en"
    assert "lang=en" in payload["final_url"]
    assert "ref=smart_route" in payload["final_url"]
