"""pgvector / NPZ store factory — graceful fallback."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.npz_store import NpzDenseStore
from src.db.schema import EMBEDDING_DIM
from src.db.store_factory import open_vector_store, probe_pgvector
from src.db.vector_store import VectorCandidate
from src.v2_pipeline import V2IntentPipeline


def test_probe_pgvector_does_not_raise():
    ok, detail = probe_pgvector()
    assert isinstance(ok, bool)
    assert isinstance(detail, str)
    assert detail


def test_open_vector_store_graceful_fallback(capsys):
    store = open_vector_store(prefer_pg=True)
    backend = getattr(store, "backend", type(store).__name__)
    assert backend in ("pgvector", "npz")
    out = capsys.readouterr().out
    assert (
        "Connected to pgvector DB" in out
        or "DB unreachable, falling back to NPZ-dense" in out
        or "NPZ-dense" in out
    )
    q = [0.0] * EMBEDDING_DIM
    q[0] = 1.0
    hits = store.search(q, top_k=3)
    assert isinstance(hits, list)
    assert len(hits) <= 3
    if hits:
        assert isinstance(hits[0], VectorCandidate)


def test_npz_store_top3_shape():
    store = NpzDenseStore()
    assert store.backend == "npz"
    assert store._vectors.shape[1] == EMBEDDING_DIM
    assert store._vectors.shape[0] >= 1000
    q = store._vectors[0]
    hits = store.search(q, top_k=3)
    assert len(hits) == 3
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_v2_pipeline_uses_fallback_store_without_crash():
    store = open_vector_store(prefer_pg=False)  # zorla NPZ
    pipe = V2IntentPipeline(
        store=store,
        embed_fn=lambda q: [0.0] * EMBEDDING_DIM,
    )
    # boş ranked → OOD; önemli olan çökmemesi
    out = pipe.run("xyz unrelated query for store wiring")
    assert out.layer in ("ml", "rule")
    assert out.latency_ms >= 0
