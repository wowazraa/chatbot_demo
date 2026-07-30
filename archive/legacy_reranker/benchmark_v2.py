"""V2 pipeline latency + accuracy kabul ölçümü.

    python scripts/benchmark_v2.py
    python scripts/benchmark_v2.py --n 50 --warmup 3
    python scripts/benchmark_v2.py --pgvector   # pgvector varsa

Hedef: ortalama / P95 latency < 150ms (warm).
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
# FlagEmbedding / tqdm gürültüsünü azalt
os.environ.setdefault("TQDM_DISABLE", "1")

import numpy as np

from src.db.schema import EMBEDDING_DIM
from src.db.npz_store import NpzDenseStore
from src.db.vector_store import VectorCandidate
from src.intent_router_contract import map_sector
from src.models.reranker import get_reranker, reset_reranker
from src.v2_pipeline import V2IntentPipeline

# gold index → EN sector (fixtures/chatbot_bench_data.PASSAGES sırası)
_GOLD_SECTOR = {
    0: "health",
    1: "tourism",
    2: "defense",
    3: "education",
    4: "ood",
}


def _bench_cases() -> list[dict[str, str]]:
    """40+ etiketli sorgu (sektör dengeli + OOD + zor vakalar)."""
    from tests.fixtures.chatbot_bench_data import HARD_CASES

    cases: list[dict[str, str]] = []
    for c in HARD_CASES:
        cases.append(
            {
                "id": c["id"],
                "query": c["query"],
                "expected": _GOLD_SECTOR.get(int(c["gold"]), "ood"),
            }
        )

    extra: list[tuple[str, str, str]] = [
        ("E01", "Kardiyoloji randevusu almak istiyorum", "health"),
        ("E02", "HBYS kurulumu için teklif istiyoruz", "health"),
        ("E03", "Kan tahlili sonucu için lab entegrasyonu", "health"),
        ("E04", "Poliklinik randevu sistemi lazım", "health"),
        ("E05", "e-Nabız entegrasyonu hakkında bilgi", "health"),
        ("E06", "Antalya'da denize sıfır otel bakıyorum", "tourism"),
        ("E07", "Müze bileti rezervasyonu yapmak istiyorum", "tourism"),
        ("E08", "PNR ve check-in otomasyonu arıyoruz", "tourism"),
        ("E09", "Resort yönetim yazılımı teklifi", "tourism"),
        ("E10", "Otel rezervasyon paneli kurmak istiyoruz", "tourism"),
        ("E11", "ASELSAN radar lojistik talep", "defense"),
        ("E12", "İHA haberleşme sistemi hakkında bilgi", "defense"),
        ("E13", "TSK komuta kontrol yazılımı", "defense"),
        ("E14", "Askeri lojistik takip platformu", "defense"),
        ("E15", "Kriptolu birlik haberleşmesi", "defense"),
        ("E16", "OBS üzerinden transkript indirme", "education"),
        ("E17", "Yaz okulu kayıt işlemleri nasıl yapılır", "education"),
        ("E18", "LMS sınav otomasyonu istiyoruz", "education"),
        ("E19", "Öğrenci harç ve kayıt sistemi", "education"),
        ("E20", "Çift anadal başvuru süreci", "education"),
        ("E21", "bugün hava çok güzel", "ood"),
        ("E22", "akşam yemeğinde ne pişireyim", "ood"),
        ("E23", "Bitcoin fiyatı ne olacak", "ood"),
        ("E24", "fiyat teklifi almak istiyorum", "ood"),
        ("E25", "genel kurumsal demo planlayalım", "ood"),
        ("E26", "Merhaba, sağlık turizmi için otel yazılımı", "tourism"),
        ("E27", "Askeri hastanede poliklinik randevu", "health"),
        ("E28", "Üniversite OBS kurulumu", "education"),
        ("E29", "Radar veri analiz yazılımı", "defense"),
        ("E30", "Klinik hasta kayıt sistemi", "health"),
    ]
    seen = {c["query"] for c in cases}
    for cid, q, exp in extra:
        if q not in seen:
            cases.append({"id": cid, "query": q, "expected": exp})
            seen.add(q)
    return cases


def _try_pg_store():
    from src.db.store_factory import open_vector_store, probe_pgvector

    ok, _ = probe_pgvector()
    if not ok:
        return None
    store = open_vector_store(prefer_pg=True)
    if getattr(store, "backend", "") != "pgvector":
        return None
    return store


@dataclass
class RowResult:
    case_id: str
    query: str
    expected: str
    predicted: str
    status: str
    latency_ms: float
    initial_score: float | None
    reranker_score: float | None
    correct: bool


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    k = (len(ys) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def _fmt_table(rows: list[tuple[str, str, str]]) -> str:
    w0 = max(len(r[0]) for r in rows)
    w1 = max(len(r[1]) for r in rows)
    w2 = max(len(r[2]) for r in rows)
    sep = f"+-{'-' * w0}-+-{'-' * w1}-+-{'-' * w2}-+"
    lines = [sep, f"| {'Metric'.ljust(w0)} | {'Value'.ljust(w1)} | {'Target / Note'.ljust(w2)} |", sep]
    for a, b, c in rows:
        lines.append(f"| {a.ljust(w0)} | {b.ljust(w1)} | {c.ljust(w2)} |")
    lines.append(sep)
    return "\n".join(lines)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="V2 latency + precision benchmark")
    ap.add_argument("--n", type=int, default=50, help="Kaç sorgu (max mevcut set)")
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--pgvector", action="store_true", help="pgvector zorunlu")
    ap.add_argument("--no-rerank-reset", action="store_true")
    args = ap.parse_args()

    cases = _bench_cases()[: max(1, args.n)]
    store = _try_pg_store()
    mode = "pgvector"
    if store is None:
        if args.pgvector:
            print("[bench] pgvector boş/yok — seed_pgvector.py gerekli")
            return 1
        print("[bench] pgvector yok → NPZ dense store (V2 Stage-1 offline)")
        store = NpzDenseStore()
        mode = "npz-dense"

    if not args.no_rerank_reset:
        reset_reranker()

    pipe = V2IntentPipeline(store=store, top_k=3)  # type: ignore[arg-type]

    print(f"[bench] mode={mode}  n={len(cases)}  warmup={args.warmup}")
    print("[bench] warm-up (model yükleme)…")
    for i in range(max(0, args.warmup)):
        q = cases[i % len(cases)]["query"]
        pipe.run(q)
    print("[bench] warm-up OK — timed koşu başlıyor\n")

    results: list[RowResult] = []
    lifts: list[float] = []
    stage_sums: dict[str, float] = {"embed_ms": 0.0, "retrieve_ms": 0.0, "rerank_ms": 0.0}

    for c in cases:
        t0 = time.perf_counter()
        out = pipe.run(c["query"])
        wall = (time.perf_counter() - t0) * 1000
        lat = float(out.latency_ms) if out.latency_ms else wall

        for k in stage_sums:
            stage_sums[k] += float((out.stages_ms or {}).get(k, 0.0))

        pred = out.sector
        top = out.top_candidates[0] if out.top_candidates else None
        init = top.get("initial_score") if top else None
        rr = top.get("reranker_score") if top else None
        if init is not None and rr is not None:
            lifts.append(float(rr) - float(init))

        if c["expected"] == "ood":
            ok = pred == "ood" or out.status == "OOD"
        else:
            ok = pred == c["expected"]

        results.append(
            RowResult(
                case_id=c["id"],
                query=c["query"],
                expected=c["expected"],
                predicted=pred,
                status=out.status,
                latency_ms=lat,
                initial_score=float(init) if init is not None else None,
                reranker_score=float(rr) if rr is not None else None,
                correct=ok,
            )
        )

    n = max(1, len(results))
    lats = [r.latency_ms for r in results]
    mean_lat = statistics.fmean(lats) if lats else 0.0
    p50 = _percentile(lats, 50)
    p95 = _percentile(lats, 95)
    p99 = _percentile(lats, 99)
    precision = sum(1 for r in results if r.correct) / n
    mean_lift = statistics.fmean(lifts) if lifts else 0.0
    avg_embed = stage_sums["embed_ms"] / n
    avg_ret = stage_sums["retrieve_ms"] / n
    avg_rr = stage_sums["rerank_ms"] / n

    pass_lat = mean_lat < 150 and p95 < 150
    table = _fmt_table(
        [
            ("Queries", str(len(results)), f"mode={mode}"),
            ("Mean Latency (ms)", f"{mean_lat:.1f}", "< 150"),
            ("P50 Latency (ms)", f"{p50:.1f}", "—"),
            ("P95 Latency (ms)", f"{p95:.1f}", "< 150"),
            ("P99 Latency (ms)", f"{p99:.1f}", "—"),
            ("  ├ embed (ms)", f"{avg_embed:.1f}", "bge-m3 query encode"),
            ("  ├ retrieve (ms)", f"{avg_ret:.1f}", "Top-3 ANN"),
            ("  └ rerank (ms)", f"{avg_rr:.1f}", "bge-reranker-v2-m3"),
            ("Latency Gate", "PASS" if pass_lat else "FAIL", "mean & P95 < 150"),
            (
                "Precision (top-1 sector)",
                f"{precision * 100:.1f}%",
                f"{sum(r.correct for r in results)}/{len(results)}",
            ),
            ("Mean Δ score (rr − bge)", f"{mean_lift:+.4f}", "reranker − initial_score"),
            ("MIN_BGE", "0.80", "SUCCESS threshold"),
        ]
    )
    print(table)

    # Kısa hata örnekleri
    misses = [r for r in results if not r.correct][:8]
    if misses:
        print("\nMisses (sample):")
        for r in misses:
            q = r.query[:60].replace("\n", " ")
            print(
                f"  [{r.case_id}] exp={r.expected} got={r.predicted}/{r.status} "
                f"lat={r.latency_ms:.0f}ms | {q}"
            )

    print("\nPer-query latency (ms) — first 10:")
    for r in results[:10]:
        mark = "✓" if r.correct else "✗"
        print(
            f"  {mark} {r.latency_ms:7.1f}  {r.expected:10}→{r.predicted:10}  "
            f"bge={r.initial_score} rr={r.reranker_score}"
        )

    return 0 if pass_lat else 2


if __name__ == "__main__":
    raise SystemExit(main())
