"""V2 duman testi: pgvector Top-3 → bge-reranker-v2-m3.

    # Canlı Postgres + model (seed sonrası):
    python scripts/test_reranker_pipeline.py

    # Postgres yoksa NPZ ile Top-3 simülasyonu + reranker:
    python scripts/test_reranker_pipeline.py --offline-npz

    # Sadece retrieval (reranker yükleme):
    python scripts/test_reranker_pipeline.py --skip-rerank
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUERIES = [
    "Kardiyoloji randevusu almak istiyorum",
    "Antalya'da denize sıfır otel bakıyorum",
    "OBS üzerinden transkript indirme",
    "ASELSAN radar lojistik talep",
    "bugün hava çok güzel",
]


class OfflineHit:
    """Offline NPZ adayi — VectorCandidate ile ayni arayuz."""

    __slots__ = (
        "id",
        "source_id",
        "sector",
        "sub_intent",
        "text_content",
        "distance",
        "score",
    )

    def __init__(
        self,
        hit_id: int,
        source_id: str,
        sector: str,
        sub_intent: str,
        text_content: str,
        distance: float,
        score: float,
    ) -> None:
        self.id = hit_id
        self.source_id = source_id
        self.sector = sector
        self.sub_intent = sub_intent
        self.text_content = text_content
        self.distance = distance
        self.score = score

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "sector": self.sector,
            "sub_intent": self.sub_intent,
            "text_content": self.text_content,
            "distance": self.distance,
            "score": self.score,
        }


def _offline_top3(query: str, top_k: int = 3) -> list:
    """V1 NPZ hybrid — yalnizca test fallback; uretim V2 yolu degil."""
    from src.embedder import get_embedder
    from src.intent_router_contract import map_sector, map_sub_intent

    emb = get_embedder()
    hits = emb.find_top_k_hybrid(query, k=top_k, alpha=0.9)
    out = []
    for h in hits:
        sector_tr = (h.metadata or {}).get("beklenen_sektor") or ""
        sector = map_sector(str(sector_tr))
        text = h.text or ""
        out.append(
            OfflineHit(
                hit_id=int(h.idx),
                source_id=str((h.metadata or {}).get("id") or h.idx),
                sector=sector,
                sub_intent=map_sub_intent(sector, text),
                text_content=text,
                distance=round(max(0.0, 1.0 - float(h.score)), 6),
                score=round(float(h.score), 6),
            )
        )
    return out


def _pg_top3(query: str, top_k: int = 3):
    from src.db.migrate import row_count, table_exists
    from src.db.vector_store import VectorIndexStore
    from src.embedder import get_embedder

    if not table_exists():
        raise RuntimeError(
            "vector_index yok — once: python scripts/seed_pgvector.py"
        )
    n = row_count()
    if n < 1:
        raise RuntimeError("vector_index bos — seed_pgvector.py calistirin")

    emb = get_embedder()
    qvec = emb.encode_dense([query])[0]
    store = VectorIndexStore()
    return store.search(qvec, top_k=top_k), n


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--offline-npz",
        action="store_true",
        help="Postgres yoksa NPZ Top-3 ile devam et",
    )
    ap.add_argument("--skip-rerank", action="store_true")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    mode = "offline-npz" if args.offline_npz else "pgvector"
    print(f"[test] mode={mode}  top_k={args.top_k}  queries={len(QUERIES)}")
    print("-" * 72)

    for q in QUERIES:
        print(f"\nQ: {q}")
        t0 = time.perf_counter()
        try:
            if args.offline_npz:
                hits = _offline_top3(q, top_k=args.top_k)
                meta = {"source": "npz", "n_index": None}
            else:
                hits, n = _pg_top3(q, top_k=args.top_k)
                meta = {"source": "pgvector", "n_index": n}
        except Exception as exc:
            print(f"  [!] retrieval hata: {exc}")
            if not args.offline_npz:
                print("  Ipucu: --offline-npz veya seed_pgvector.py")
            return 1

        retrieve_ms = (time.perf_counter() - t0) * 1000
        print(f"  retrieval ({meta['source']}) {retrieve_ms:.1f}ms  hits={len(hits)}")
        for i, h in enumerate(hits, 1):
            text = h.text_content[:80].replace("\n", " ")
            print(
                f"    #{i} score={h.score:.4f}  {h.sector}/{h.sub_intent}  | {text}"
            )

        if args.skip_rerank:
            continue

        from src.models.reranker import get_reranker

        t1 = time.perf_counter()
        rr = get_reranker()
        ranked = rr.rerank(q, hits, top_k=args.top_k)
        rerank_ms = (time.perf_counter() - t1) * 1000
        total_ms = (time.perf_counter() - t0) * 1000
        print(f"  rerank {rerank_ms:.1f}ms  total={total_ms:.1f}ms")
        for i, r in enumerate(ranked, 1):
            c = r.candidate
            sector = getattr(c, "sector", "?")
            sub = getattr(c, "sub_intent", "?")
            print(f"    R#{i} ce_score={r.score:.4f}  {sector}/{sub}")

        best = ranked[0] if ranked else None
        from src.intent_router_contract import (
            build_top_candidate,
            resolve_redirect_url,
            resolve_response_message,
        )

        top_candidates = []
        for r in ranked:
            c = r.candidate
            top_candidates.append(
                build_top_candidate(
                    text=r.text,
                    sector=str(getattr(c, "sector", "ood")),
                    sub_intent=str(getattr(c, "sub_intent", "ood.none")),
                    initial_score=float(getattr(c, "score", 0.0)),
                    reranker_score=float(r.score),
                )
            )

        if best is None:
            sector, sub, conf, status = "ood", "ood.none", 0.0, "OOD"
        else:
            conf = float(best.score)
            sector = getattr(best.candidate, "sector", "ood")
            sub = getattr(best.candidate, "sub_intent", "ood.none")
            if conf >= 0.80 and sector != "ood":
                status = "SUCCESS"
            elif conf >= 0.45:
                status = "UNCERTAIN"
            else:
                status = "OOD"
                sector, sub = "ood", "ood.none"

        redirect_url = resolve_redirect_url(str(sector), str(sub), status)
        response_message = resolve_response_message(
            str(sector), str(sub), status, redirect_url=redirect_url
        )
        payload = {
            "query": q,
            "intent": {
                "sector": sector,
                "sub_intent": sub,
                "confidence_score": round(float(conf), 4),
            },
            "status": status,
            "latency_ms": int(round(total_ms)),
            "response_message": response_message,
            "redirect_url": redirect_url,
            "top_candidates": top_candidates,
        }
        print("  contract:", json.dumps(payload, ensure_ascii=False, indent=2))

    print("\n" + "-" * 72)
    print("[test] OK — V1 Chatbot/NPZ pipeline değiştirilmedi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
