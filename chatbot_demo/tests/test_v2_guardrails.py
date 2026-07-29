"""2 katmanlı V2 koruma — fast-path + K1 regex + strict 0.65 threshold gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chitchat_rules import MSG_ABUSE, MSG_GIBBERISH, MSG_GREETING, MSG_THANKS, match_fast_path
from src.db.schema import EMBEDDING_DIM
from src.db.vector_store import VectorCandidate
from src.k1_guardrails import check_restricted_domain, extract_active_clause
from src.v2_pipeline import V2IntentPipeline


def test_fast_path_greeting():
    hit = match_fast_path("Merhaba")
    assert hit is not None
    assert hit.category == "greeting"
    assert hit.redirect_url == ""
    assert hit.response_message == MSG_GREETING


def test_fast_path_thanks():
    hit = match_fast_path("Teşekkürler")
    assert hit is not None
    assert hit.category == "thanks"
    assert hit.response_message == MSG_THANKS


def test_fast_path_stacked_thanks():
    # Kelime sayısı tuzak değil; saf sosyal yığın → thanks
    hit = match_fast_path("Teşekkür ederim, sağ olun")
    assert hit is not None
    assert hit.category == "thanks"
    assert hit.response_message == MSG_THANKS
    assert match_fast_path("Çok teşekkürler sağol") is not None
    assert match_fast_path("Merhaba, teşekkürler") is not None


def test_fast_path_gibberish():
    hit = match_fast_path("asdasd")
    assert hit is not None
    assert hit.category == "gibberish"
    assert hit.status == "OOD"
    assert hit.response_message == MSG_GIBBERISH


def test_fast_path_abuse():
    hit = match_fast_path("salak mısın")
    assert hit is not None
    assert hit.category == "abuse"
    assert hit.response_message == MSG_ABUSE


def test_fast_path_skips_contentful_greeting():
    # Sosyal + gerçek talep artığı → ML'ye bırak
    assert match_fast_path("Merhaba, kardiyoloji randevusu almak istiyorum") is None
    assert match_fast_path("Selam, hastane randevusu nasıl alınır?") is None
    assert match_fast_path("iyi akşamlar askeri radar sistemi") is None
    assert match_fast_path("Teşekkürler, LMS kuracağız") is None


def test_pipeline_greeting_no_model():
    class BoomStore:
        def search(self, *a, **k):
            raise AssertionError("ML çalışmamalı")

    pipe = V2IntentPipeline(
        store=BoomStore(),  # type: ignore[arg-type]
        embed_fn=lambda q: (_ for _ in ()).throw(AssertionError("embed yok")),
    )
    out = pipe.run("merhaba")
    assert out.layer == "rule"
    assert out.redirect_url == ""
    assert out.top_candidates == []
    assert out.response_message == MSG_GREETING
    assert out.latency_ms < 50  # model yok; rahat sınır
    payload = out.to_intent_router()
    assert payload["redirect_url"] == ""
    assert payload["top_candidates"] == []


def test_pipeline_gibberish():
    pipe = V2IntentPipeline(
        store=type("S", (), {"search": lambda *a, **k: []})(),  # type: ignore[arg-type]
        embed_fn=lambda q: [0.0] * EMBEDDING_DIM,
    )
    out = pipe.run("asdasd")
    assert out.layer == "rule"
    assert out.status == "OOD"
    assert out.redirect_url == ""


def test_pipeline_k1_regex_fast_path_skips_embedding():
    """B2B jargon → K1 regex ACCEPT, embedding/retrieval hiç çağrılmaz."""

    class BoomStore:
        def search(self, *a, **k):
            raise AssertionError("K1 regex eşleşince retrieval çalışmamalı")

    pipe = V2IntentPipeline(
        store=BoomStore(),  # type: ignore[arg-type]
        embed_fn=lambda q: (_ for _ in ()).throw(AssertionError("K1 eşleşince embed olmamalı")),
    )
    out = pipe.run("bulut yazılım ve entegrasyonu")
    assert out.layer == "rule"
    assert out.status == "SUCCESS"
    assert out.sector == "bilisim"
    assert out.confidence_score == 0.99
    assert out.redirect_url == "/bilisim"
    assert out.latency_ms < 50

    out2 = pipe.run("klinik doktor ve hasta takibi")
    assert out2.sector == "saglik"
    assert out2.confidence_score == 0.99
    assert out2.status == "SUCCESS"


def test_pipeline_health_success_and_ood_gate():
    class FakeStoreHigh:
        def search(self, qvec, top_k=3, sector=None):
            # BGE top1 0.9 >= 0.65 → strict gate ACCEPT
            return [
                VectorCandidate(1, "1", "health", "health.appointment", "randevu", 0.1, 0.9),
                VectorCandidate(2, "2", "health", "health.general", "hastane", 0.2, 0.8),
                VectorCandidate(3, "3", "tourism", "tourism.hotel", "otel", 0.3, 0.7),
            ][:top_k]

    class FakeStoreLow:
        def search(self, qvec, top_k=3, sector=None):
            # BGE top1 0.50 < 0.65 → strict gate REJECT (OOD)
            return [
                VectorCandidate(1, "1", "health", "health.appointment", "randevu", 0.1, 0.50),
                VectorCandidate(2, "2", "tourism", "tourism.hotel", "otel", 0.2, 0.45),
            ][:top_k]

    high = V2IntentPipeline(
        store=FakeStoreHigh(),  # type: ignore[arg-type]
        embed_fn=lambda q: [0.0] * EMBEDDING_DIM,
    ).run("kardiyoloji için bir şeyler")
    assert high.layer == "ml"
    assert high.status == "SUCCESS"
    assert high.redirect_url == "/saglik"
    assert len(high.top_candidates) == 3
    assert abs(high.confidence_score - 0.9) < 1e-6

    low = V2IntentPipeline(
        store=FakeStoreLow(),  # type: ignore[arg-type]
        embed_fn=lambda q: [0.0] * EMBEDDING_DIM,
    ).run("Süper lig şampiyonu kim?")
    assert low.status == "OOD"
    assert low.sector == "ood"
    assert low.redirect_url == ""
    assert "yardımcı olamıyorum" in low.response_message.lower()


# ── STEP 2: extract_active_clause (tamamlanmış eylem temizliği) ─────────────

def test_extract_active_clause_drops_completed_tr():
    assert extract_active_clause("Poliklinik hallettik, kantin için teklif istiyoruz") == "kantin için teklif istiyoruz"


def test_extract_active_clause_drops_completed_en():
    active = extract_active_clause(
        "We already sorted out the clinical appointment system, "
        "now we need a quote for an in-hospital cafeteria automation."
    )
    assert "sorted out" not in active.lower()
    assert "cafeteria automation" in active.lower()


def test_extract_active_clause_no_trigger_returns_original():
    q = "Klinik otomasyonu için teklif istiyoruz"
    assert extract_active_clause(q) == q


def test_extract_active_clause_all_clauses_discarded_falls_back():
    q = "Zaten hallettik, tamamladık"
    assert extract_active_clause(q) == q


# ── STEP 3: check_restricted_domain (hard OOD blocklist) ────────────────────

def test_restricted_domain_legal():
    assert check_restricted_domain("Avukatlar hakkında dava dosyasını görmek istiyoruz") is True


def test_restricted_domain_real_estate():
    assert check_restricted_domain("Gayrimenkul portföyümüz için kiralık daireler arıyoruz") is True


def test_restricted_domain_finance():
    assert check_restricted_domain("Bankacılık işlemleri için kredi kartı başvurusu") is True


def test_restricted_domain_defense():
    assert check_restricted_domain("Askeri İHA için roket ve mühimmat fiyatları") is True


def test_restricted_domain_energy():
    assert check_restricted_domain("Rüzgar türbinlerinin elektrik üretim kapasitesi") is True


def test_restricted_domain_food_service():
    assert check_restricted_domain("Hastane kantini ve yemekhane yemek listesi") is True


def test_restricted_domain_ignores_completed_clause():
    # "poliklinik" tamamlanmış eylem clause'unda -> STEP 2 tarafından atılır.
    # Kalan aktif talep (kantin) zaten yasaklı, dolayısıyla True bekleniyor.
    assert check_restricted_domain("Poliklinik hallettik, kantin için teklif istiyoruz") is True


def test_restricted_domain_allows_legit_sectors():
    assert check_restricted_domain("Sürücü kursu için otomasyon arıyoruz") is False
    assert check_restricted_domain("Klinik otomasyonu için teklif istiyoruz") is False
    assert check_restricted_domain("CI/CD pipeline ve kubernetes orkestrasyonu istiyoruz") is False


def test_pipeline_hard_blocklist_skips_embedding():
    """Yasaklı sektör -> embedding/retrieval hiç çağrılmaz, anında OOD."""

    class BoomStore:
        def search(self, *a, **k):
            raise AssertionError("Restricted domain'de retrieval çalışmamalı")

    pipe = V2IntentPipeline(
        store=BoomStore(),  # type: ignore[arg-type]
        embed_fn=lambda q: (_ for _ in ()).throw(AssertionError("Restricted domain'de embed olmamalı")),
    )

    out = pipe.run(
        "We already sorted out the clinical appointment system, "
        "now we need a quote for an in-hospital cafeteria."
    )
    assert out.layer == "rule"
    assert out.status == "OOD"
    assert out.sector == "ood"
    assert out.redirect_url == ""

    out2 = pipe.run("Poliklinik hallettik, kantin için fiyat teklifi istiyoruz")
    assert out2.status == "OOD"
    assert out2.sector == "ood"

    out3 = pipe.run("Avukatlar hakkında dava dosyası istiyoruz")
    assert out3.status == "OOD"
    assert out3.sector == "ood"
