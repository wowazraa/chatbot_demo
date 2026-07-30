"""
Chatbot Bilgi Merkezi — Birlesik Benchmark Suite
================================================
Tek komut, uc parca; hepsi proje domain'i (4 sektor) uzerinden:

  A) 3 model siralama (bge-m3 / reranker-large / reranker-v2-m3)
  B) v2-m3 PyTorch vs ONNX (sure + CPU)
  C) ChromaDB (gercek embeddings.npz) vs PGVector disk kuyrugu (50 eszamanli)

Calistir:
    python tests/benchmark_chatbot_suite.py
    python tests/benchmark_chatbot_suite.py --only models
    python tests/benchmark_chatbot_suite.py --only onnx
    python tests/benchmark_chatbot_suite.py --only db

Gereksinim:
    pip install transformers torch onnxruntime psutil numpy chromadb
    pip install "optimum[onnxruntime]"   # ONNX parcasi icin
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from fixtures.chatbot_bench_data import (  # noqa: E402
    HARD_CASES,
    MODELS,
    ONNX_PASSAGES,
    ONNX_QUERY,
    PASSAGES,
    RERANKER_ID,
    SEKTOR,
    build_cases,
)

THREADS = 4
# Sure: buyuk n icin 1 timed (warmup ayri); kucuk n icin 1 warmup + 1 timed
MODEL_LOOPS = 2
MODEL_WARMUP = 1
ONNX_LOOPS = 8
ONNX_WARMUP = 1
ONNX_DIR = TESTS / "_reranker_onnx_cache"
DB_USERS = 50
DB_SUBSET = 2000  # gercek indeksten ornek
PG_DISK_IO_MS = 15
INDEX_NPZ = ROOT / "data" / "processed" / "embeddings.npz"
INDEX_META = ROOT / "data" / "processed" / "index_meta.json"

DEFAULT_N_CASES = 1000


def _log(msg: str = "") -> None:
    print(msg, flush=True)


def _free_torch() -> None:
    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ===========================================================================
# A) 3 MODEL
# ===========================================================================
@dataclass
class CaseScore:
    case_id: str
    zorluk: str
    ranking: list[int]
    top1_ok: bool
    margin: float
    ms: float


@dataclass
class ModelReport:
    name: str
    kind: str
    ok: bool
    note: str = ""
    cases: list[CaseScore] = field(default_factory=list)
    avg_ms: float = 0.0
    top1_acc: float = 0.0
    avg_margin: float = 0.0
    by_zorluk: dict[str, float] = field(default_factory=dict)


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.maximum(n, 1e-12)


def _score_bi(model, tokenizer, query: str, passages: list[str]) -> list[float]:
    import torch

    texts = [query] + passages
    inputs = tokenizer(
        texts, padding=True, truncation=True, return_tensors="pt", max_length=512
    )
    with torch.no_grad():
        out = model(**inputs)
        hidden = out.last_hidden_state
        mask = inputs["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        emb = torch.sum(hidden * mask, dim=1) / torch.clamp(mask.sum(dim=1), min=1e-9)
        emb = emb.cpu().numpy()
    emb = _l2(emb)
    return (emb[1:] @ emb[0]).astype(float).tolist()


def _score_cross(model, tokenizer, query: str, passages: list[str]) -> list[float]:
    import torch

    pairs = [[query, p] for p in passages]
    inputs = tokenizer(
        pairs, padding=True, truncation=True, return_tensors="pt", max_length=512
    )
    with torch.no_grad():
        logits = model(**inputs).logits.view(-1).float()
    return [float(x) for x in logits.tolist()]


def _margin(scores: list[float], gold: int) -> float:
    best_other = max(s for i, s in enumerate(scores) if i != gold)
    return float(scores[gold] - best_other)


def _run_one_model(
    name: str, path: str, kind: str, cases_in: list[dict], idx: int, total: int
) -> ModelReport:
    import torch
    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

    _log(f"\n  --- [{idx}/{total}] {name} yukleniyor ({path}) ---")
    torch.set_num_threads(THREADS)
    model = None
    tok = None
    try:
        tok = AutoTokenizer.from_pretrained(path, local_files_only=False)
        _log("  tokenizer OK, model agirliklari yukleniyor...")
        if kind == "bi":
            model = AutoModel.from_pretrained(path)
            fn = _score_bi
        else:
            model = AutoModelForSequenceClassification.from_pretrained(path)
            fn = _score_cross
        model.eval()
        _log(f"  model hazir | {len(cases_in)} vaka")
    except Exception as exc:
        _log(f"  [!] Yukleme hatasi: {exc}")
        _free_torch()
        return ModelReport(name, kind, False, str(exc))

    verbose = len(cases_in) <= 40
    loops = MODEL_LOOPS if len(cases_in) <= 100 else 1
    warmup = MODEL_WARMUP if loops > 1 else 0

    _ = fn(model, tok, cases_in[0]["query"], PASSAGES)
    cases: list[CaseScore] = []
    n = len(cases_in)
    fail_n = 0
    for j, c in enumerate(cases_in, 1):
        times: list[float] = []
        scores: list[float] = []
        for i in range(max(loops, 1)):
            t0 = time.perf_counter()
            scores = fn(model, tok, c["query"], PASSAGES)
            ms = (time.perf_counter() - t0) * 1000.0
            if i >= warmup:
                times.append(ms)
        ranking = list(np.argsort(scores)[::-1].astype(int))
        gold = int(c["gold"])
        ok = ranking[0] == gold
        m = _margin(scores, gold)
        avg_ms = float(np.mean(times)) if times else 0.0
        if not ok:
            fail_n += 1
        if verbose:
            mark = "OK" if ok else "FAIL"
            _log(
                f"  [{mark}] {c['id']:<4} {c['zorluk']:<8} "
                f"top={SEKTOR[ranking[0]]:<8} gold={SEKTOR[gold]:<8} "
                f"marj={m:+.3f} {avg_ms:.0f}ms | {c['not']}"
            )
        elif j % 100 == 0 or j == n:
            acc_so_far = (j - fail_n) / j
            _log(
                f"  ... {j}/{n} | anlik Top1={100 * acc_so_far:.1f}% | "
                f"fail={fail_n} | son={avg_ms:.0f}ms"
            )
        cases.append(CaseScore(c["id"], c["zorluk"], ranking, ok, m, avg_ms))

    del model, tok
    _free_torch()
    _log(f"  --- {name} bitti | Top1={100 * np.mean([c.top1_ok for c in cases]):.1f}% ---")

    by: dict[str, list[bool]] = {}
    for cs in cases:
        by.setdefault(cs.zorluk, []).append(cs.top1_ok)
    return ModelReport(
        name=name,
        kind=kind,
        ok=True,
        cases=cases,
        avg_ms=float(np.mean([c.ms for c in cases])),
        top1_acc=float(np.mean([c.top1_ok for c in cases])),
        avg_margin=float(np.mean([c.margin for c in cases])),
        by_zorluk={k: sum(v) / len(v) for k, v in by.items()},
    )


def part_a_models(cases_in: list[dict]) -> list[ModelReport]:
    _log("\n" + "=" * 72)
    _log(f"  A) 3 MODEL SIRALAMA (chatbot domain — {len(cases_in)} vaka)")
    _log("=" * 72)
    items = list(MODELS.items())
    reports: list[ModelReport] = []
    for i, (n, (p, k)) in enumerate(items, 1):
        reports.append(_run_one_model(n, p, k, cases_in, i, len(items)))

    _log("\n  MODEL SECIM MATRISI")
    _log(
        f"  {'Model':<22} {'Tur':<6} {'Top1%':>7} {'Marj':>8} {'Ort(ms)':>8}  "
        f"hard  corpus"
    )
    _log("  " + "-" * 72)
    for r in reports:
        if not r.ok:
            _log(f"  {r.name:<22} FAIL")
            continue
        z = r.by_zorluk
        hard_keys = ("net", "negasyon", "metafor", "capraz", "gurultu")
        hard_vals = [z[k] for k in hard_keys if k in z]
        hard_acc = (sum(hard_vals) / len(hard_vals)) if hard_vals else 0.0
        corp_acc = z.get("corpus", 0.0)
        _log(
            f"  {r.name:<22} {r.kind:<6} {100 * r.top1_acc:6.1f}% "
            f"{r.avg_margin:+7.3f} {r.avg_ms:8.1f}  "
            f"{100 * hard_acc:5.1f} {100 * corp_acc:6.1f}"
        )
    for r in reports:
        if not r.ok:
            continue
        fails = [c for c in r.cases if not c.top1_ok]
        if not fails:
            _log(f"  FAIL {r.name}: (yok)")
        else:
            # en fazla 12 fail goster
            sample = fails[:12]
            ids = ", ".join(f"{c.case_id}->{SEKTOR[c.ranking[0]]}" for c in sample)
            extra = f" (+{len(fails) - 12})" if len(fails) > 12 else ""
            _log(f"  FAIL {r.name}: {ids}{extra}")
    return reports


# ===========================================================================
# B) ONNX vs PyTorch (v2-m3, chatbot query)
# ===========================================================================
def _cpu() -> float:
    try:
        import psutil

        return psutil.cpu_percent(interval=0.05)
    except ImportError:
        return 0.0


def part_b_onnx() -> dict:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    _log("\n" + "=" * 72)
    _log("  B) v2-m3 PyTorch vs ONNX (chatbot negasyon sorgusu)")
    _log("=" * 72)
    _log(f"  Query: {ONNX_QUERY}")
    _log(f"  Aday : {len(ONNX_PASSAGES)} sektor passage")
    _log("  v2-m3 yukleniyor...")

    tok = AutoTokenizer.from_pretrained(RERANKER_ID)
    model = AutoModelForSequenceClassification.from_pretrained(RERANKER_ID)
    model.eval()
    torch.set_num_threads(THREADS)
    _log("  PyTorch model hazir, olcum basliyor...")

    def score_torch() -> list[float]:
        pairs = [[ONNX_QUERY, p] for p in ONNX_PASSAGES]
        inputs = tok(
            pairs, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        with torch.no_grad():
            return model(**inputs).logits.view(-1).float().tolist()

    _ = score_torch()
    py_times: list[float] = []
    py_cpus: list[float] = []
    py_scores: list[float] = []
    for i in range(ONNX_LOOPS):
        c0 = _cpu()
        t0 = time.perf_counter()
        py_scores = score_torch()
        ms = (time.perf_counter() - t0) * 1000.0
        c1 = _cpu()
        if i >= ONNX_WARMUP:
            py_times.append(ms)
            py_cpus.append(max(c0, c1))
    avg_py = float(np.mean(py_times))
    avg_py_cpu = float(np.mean(py_cpus)) if py_cpus else 0.0
    _log(f"  PyTorch: {avg_py:.2f} ms | CPU ~%{avg_py_cpu:.1f}")
    _log(f"  Skorlar: {[round(s, 3) for s in py_scores]}")

    out: dict = {
        "pytorch_ms": avg_py,
        "pytorch_cpu": avg_py_cpu,
        "pytorch_scores": py_scores,
        "onnx_ms": None,
        "onnx_cpu": None,
        "speedup": None,
        "skipped": False,
    }

    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification
    except ImportError:
        _log("  [!] optimum yok — ONNX atlandi (pip install 'optimum[onnxruntime]')")
        del model, tok
        _free_torch()
        out["skipped"] = True
        return out

    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    if not (ONNX_DIR / "model.onnx").exists():
        _log("  [+] ONNX export (ilk sefer uzun, bekleyin)...")
        try:
            ort = ORTModelForSequenceClassification.from_pretrained(
                RERANKER_ID, export=True, provider="CPUExecutionProvider"
            )
            ort.save_pretrained(ONNX_DIR)
            tok.save_pretrained(ONNX_DIR)
            _log("  [+] ONNX export tamam")
        except Exception as exc:
            _log(f"  [!] ONNX export basarisiz: {exc}")
            traceback.print_exc()
            del model, tok
            _free_torch()
            out["skipped"] = True
            return out
    else:
        _log(f"  [+] ONNX cache: {ONNX_DIR}")

    ort_model = ORTModelForSequenceClassification.from_pretrained(
        ONNX_DIR, provider="CPUExecutionProvider"
    )
    _log("  ONNX model hazir, olcum...")

    def score_onnx() -> list[float]:
        pairs = [[ONNX_QUERY, p] for p in ONNX_PASSAGES]
        inputs = tok(
            pairs, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        with torch.no_grad():
            return ort_model(**inputs).logits.view(-1).float().tolist()

    _ = score_onnx()
    ox_times: list[float] = []
    ox_cpus: list[float] = []
    ox_scores: list[float] = []
    for i in range(ONNX_LOOPS):
        c0 = _cpu()
        t0 = time.perf_counter()
        ox_scores = score_onnx()
        ms = (time.perf_counter() - t0) * 1000.0
        c1 = _cpu()
        if i >= ONNX_WARMUP:
            ox_times.append(ms)
            ox_cpus.append(max(c0, c1))
    avg_ox = float(np.mean(ox_times))
    avg_ox_cpu = float(np.mean(ox_cpus)) if ox_cpus else 0.0
    speedup = avg_py / max(avg_ox, 1e-6)
    _log(f"  ONNX   : {avg_ox:.2f} ms | CPU ~%{avg_ox_cpu:.1f}")
    _log(f"  Skorlar: {[round(s, 3) for s in ox_scores]}")
    _log(f"  Hiz    : ONNX ~{speedup:.2f}x PyTorch")

    del model, tok, ort_model
    _free_torch()

    out.update(
        {
            "onnx_ms": avg_ox,
            "onnx_cpu": avg_ox_cpu,
            "onnx_scores": ox_scores,
            "speedup": speedup,
        }
    )
    return out


# ===========================================================================
# C) DB concurrent — gercek embeddings.npz
# ===========================================================================
async def part_c_db() -> dict:
    _log("\n" + "=" * 72)
    _log("  C) ChromaDB (proje index) vs PGVector disk kuyrugu")
    _log("=" * 72)

    if not INDEX_NPZ.exists() or not INDEX_META.exists():
        _log(f"  [!] Index yok: {INDEX_NPZ}")
        _log("      Once: python scripts/build_index.py")
        return {"skipped": True}

    import chromadb

    vecs = np.load(INDEX_NPZ)["vectors"].astype(np.float32)
    meta = json.loads(INDEX_META.read_text(encoding="utf-8"))
    texts: list[str] = meta["texts"]
    metas: list[dict] = meta["meta"]
    n = min(DB_SUBSET, len(vecs), len(texts))
    idx = np.linspace(0, len(vecs) - 1, n, dtype=int)
    vecs_s = vecs[idx]
    texts_s = [texts[i] for i in idx]
    meta_s = [metas[i] for i in idx]
    dim = int(vecs_s.shape[1])
    _log(f"  Kaynak: embeddings.npz | ornek={n} | dim={dim}")
    sectors: dict[str, int] = {}
    for m in meta_s:
        s = m.get("beklenen_sektor", "?")
        sectors[s] = sectors.get(s, 0) + 1
    _log(f"  Sektor dagilimi: {sectors}")

    client = chromadb.EphemeralClient()
    col = client.create_collection(name="chatbot_niyetler")
    batch = 200
    for start in range(0, n, batch):
        end = min(start + batch, n)
        col.add(
            embeddings=vecs_s[start:end].tolist(),
            documents=texts_s[start:end],
            metadatas=[
                {
                    "sektor": str(meta_s[i].get("beklenen_sektor", "")),
                    "mod": str(meta_s[i].get("beklenen_mod", "")),
                }
                for i in range(start, end)
            ],
            ids=[f"id_{i}" for i in range(start, end)],
        )
        if (start // batch) % 3 == 0:
            _log(f"  ... Chroma yukleme {end}/{n}")
    _log(f"  [+] Chroma hazir: chatbot_niyetler ({n})")

    query_vecs = [vecs_s[i % n].tolist() for i in range(DB_USERS)]

    async def chroma_one(qid: int) -> float:
        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()
        await loop.run_in_executor(
            None,
            lambda: col.query(query_embeddings=[query_vecs[qid]], n_results=3),
        )
        await asyncio.sleep(0.002)
        return (time.perf_counter() - t0) * 1000.0

    async def pg_one(_qid: int, lock: asyncio.Lock) -> float:
        t0 = time.perf_counter()
        async with lock:
            await asyncio.sleep(PG_DISK_IO_MS / 1000.0)
        return (time.perf_counter() - t0) * 1000.0

    _log(f"  [1/2] ChromaDB RAM — {DB_USERS} eszamanli...")
    chroma_ms = await asyncio.gather(*[chroma_one(i) for i in range(DB_USERS)])
    _log(f"  [2/2] PGVector disk kuyrugu — {DB_USERS} eszamanli...")
    lock = asyncio.Lock()
    pg_ms = await asyncio.gather(*[pg_one(i, lock) for i in range(DB_USERS)])

    ca = np.array(chroma_ms, dtype=np.float64)
    pa = np.array(pg_ms, dtype=np.float64)
    oran = float(pa.mean() / max(ca.mean(), 1e-6))
    _log(
        f"  Chroma  min/ort/p95/max: "
        f"{ca.min():.1f} / {ca.mean():.1f} / {np.percentile(ca, 95):.1f} / {ca.max():.1f} ms"
    )
    _log(
        f"  PG-sim  min/ort/p95/max: "
        f"{pa.min():.1f} / {pa.mean():.1f} / {np.percentile(pa, 95):.1f} / {pa.max():.1f} ms"
    )
    _log(f"  Sonuc: Chroma (RAM) ortalama ~{oran:.1f}x daha hizli (proje vektorleri)")

    return {
        "skipped": False,
        "n": n,
        "dim": dim,
        "chroma_mean": float(ca.mean()),
        "chroma_p95": float(np.percentile(ca, 95)),
        "pg_mean": float(pa.mean()),
        "pg_p95": float(np.percentile(pa, 95)),
        "speedup": oran,
    }


# ===========================================================================
# Ozet + main
# ===========================================================================
def print_final(
    reports: list[ModelReport] | None,
    onnx: dict | None,
    db: dict | None,
) -> None:
    _log("\n" + "=" * 72)
    _log("  BIRLESIK OZET — Chatbot Bilgi Merkezi Benchmark")
    _log("=" * 72)
    if reports is not None:
        _log("  [A] Model secimi (Top-1 / marj / ms):")
        for r in reports:
            if r.ok:
                _log(
                    f"      {r.name:<22} {100 * r.top1_acc:5.1f}%  "
                    f"marj={r.avg_margin:+.3f}  {r.avg_ms:.0f} ms"
                )
    if onnx is not None:
        if onnx.get("skipped"):
            _log("  [B] ONNX: atlandi")
        else:
            _log(
                f"  [B] v2-m3 PyTorch {onnx['pytorch_ms']:.1f} ms -> "
                f"ONNX {onnx.get('onnx_ms', 0):.1f} ms "
                f"(~{onnx.get('speedup', 0):.2f}x)"
            )
    if db is not None:
        if db.get("skipped"):
            _log("  [C] DB: atlandi (index yok)")
        else:
            _log(
                f"  [C] Chroma {db['chroma_mean']:.1f} ms vs "
                f"PG-sim {db['pg_mean']:.1f} ms "
                f"(~{db['speedup']:.1f}x) | n={db['n']} dim={db['dim']}"
            )
    _log("=" * 72)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Chatbot birlesik benchmark suite")
    ap.add_argument(
        "--only",
        choices=["models", "onnx", "db", "all"],
        default="all",
        help="Sadece bir parca calistir (varsayilan: all)",
    )
    ap.add_argument(
        "--n",
        type=int,
        default=DEFAULT_N_CASES,
        help=f"Model kisminda vaka sayisi (varsayilan {DEFAULT_N_CASES})",
    )
    ap.add_argument(
        "--fast",
        action="store_true",
        help="Sadece 20 sert vaka (duman testi)",
    )
    args = ap.parse_args()
    only = args.only
    if args.fast:
        cases_in = [dict(c) for c in HARD_CASES]
    else:
        cases_in = build_cases(n=args.n)

    _log("=" * 72)
    _log("  CHATBOT BILGI MERKEZI — BIRLESIK BENCHMARK SUITE")
    _log("  Domain: saglik / turizm / savunma / egitim (+ belirsiz)")
    _log(f"  Model vakalari: {len(cases_in)} (20 sert + corpus)")
    if args.fast:
        _log("  MOD: --fast (sadece HARD_CASES)")
    _log("  Not: 1000 vaka x 3 model uzun surebilir; ilerleme her 100'de bir.")
    _log("=" * 72)

    reports = None
    onnx = None
    db = None

    if only in ("all", "models"):
        reports = part_a_models(cases_in)
    if only in ("all", "onnx"):
        onnx = part_b_onnx()
    if only in ("all", "db"):
        db = asyncio.run(part_c_db())

    print_final(reports, onnx, db)


if __name__ == "__main__":
    main()
