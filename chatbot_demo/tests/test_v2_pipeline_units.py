"""V2 birimleri — mock backend / DB'siz duman testleri (reranker kaldırıldı)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.schema import EMBEDDING_DIM, TABLE_NAME
from src.db.vector_store import _vec_literal
from src.k1_guardrails import DECISION_THRESHOLD, check_ood_reject, match_any_sector
from src.v2_pipeline import V2IntentPipeline


def test_schema_constants():
    assert EMBEDDING_DIM == 1024
    assert TABLE_NAME == "vector_index"


def test_vec_literal_dim():
    lit = _vec_literal([0.0] * EMBEDDING_DIM)
    assert lit.startswith("[") and lit.endswith("]")
    assert lit.count(",") == EMBEDDING_DIM - 1


def test_decision_threshold_is_strict_065():
    assert DECISION_THRESHOLD == 0.65


def test_k1_regex_matches_b2b_jargon():
    assert match_any_sector("bulut sunucu ve yazılım altyapısı") == "bilisim"
    assert match_any_sector("hasta randevu ve poliklinik entegrasyonu") == "saglik"
    assert match_any_sector("RFQ talebi MIL-STD uyumlu") is None
    assert match_any_sector("uzaktan eğitim öğrenci ders programı") == "egitim"
    assert match_any_sector("otel rezervasyon ve konaklama acentesi") == "turizm"
    assert match_any_sector("bugün hava nasıl") is None


def test_ood_fast_reject_catches_b2c_chitchat():
    assert check_ood_reject("bugün hava nasıl") is True
    assert check_ood_reject("nasılsın") is True
    assert check_ood_reject("fıkra anlatır mısın") is True
    assert check_ood_reject("YKS puanım kaç") is True
    assert check_ood_reject("ağrı kesici önerir misin") is True
    assert check_ood_reject("IP67 gömülü yazılım") is False
    assert check_ood_reject("HL7 FHIR entegrasyonu") is False


def test_pipeline_ood_reject_skips_embedding():
    class BoomStore:
        def search(self, *a, **k):
            raise AssertionError("OOD reject eşleşince retrieval çalışmamalı")

    pipe = V2IntentPipeline(
        store=BoomStore(),  # type: ignore[arg-type]
        embed_fn=lambda q: (_ for _ in ()).throw(AssertionError("OOD reject eşleşince embed olmamalı")),
    )
    out = pipe.run("bugün hava nasıl")
    assert out.layer == "rule"
    assert out.status == "OOD"
    assert out.sector == "ood"
    assert out.redirect_url == ""
    assert out.latency_ms < 50


def test_v2_pipeline_accepts_bge_at_or_above_threshold():
    class FakeStore:
        def search(self, qvec, top_k=3, sector=None):
            from src.db.vector_store import VectorCandidate

            return [
                VectorCandidate(1, "1", "saglik", "saglik.randevu", "randevu", 0.1, 0.69),
                VectorCandidate(2, "2", "saglik", "saglik.genel", "hastane", 0.2, 0.60),
                VectorCandidate(3, "3", "saglik", "saglik.otel", "otel", 0.3, 0.55),
            ][:top_k]

    pipe = V2IntentPipeline(
        store=FakeStore(),  # type: ignore[arg-type]
        embed_fn=lambda q: [0.0] * EMBEDDING_DIM,
        top_k=3,
    )
    result = pipe.run("Kardiyoloji randevusu")
    assert result.status == "SUCCESS"
    assert result.sector == "saglik"
    assert result.sub_intent == "saglik.randevu"
    assert result.redirect_url == "/saglik"
    assert len(result.top_candidates) == 3
    assert abs(result.confidence_score - 0.85) < 1e-6
    assert result.top_candidates[0]["initial_score"] == 0.69
    assert result.top_candidates[0]["final_score"] == 0.69
    payload = result.to_intent_router()
    assert payload["redirect_url"] == "/saglik"


def test_v2_pipeline_rejects_bge_below_threshold():
    class FakeStore:
        def search(self, qvec, top_k=3, sector=None):
            from src.db.vector_store import VectorCandidate

            return [
                VectorCandidate(1, "1", "health", "health.appointment", "randevu", 0.1, 0.50),
            ][:top_k]

    pipe = V2IntentPipeline(
        store=FakeStore(),  # type: ignore[arg-type]
        embed_fn=lambda q: [0.0] * EMBEDDING_DIM,
        top_k=3,
    )
    result = pipe.run("belirsiz bir sorgu")
    assert result.status == "OOD"
    assert result.sector == "ood"
    assert result.redirect_url == ""
