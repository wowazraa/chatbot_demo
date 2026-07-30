"""V2 Stage-1 offline retrieval — clean_v1 NPZ dense cosine (pgvector yokken)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np

from src.db.schema import EMBEDDING_DIM
from src.db.vector_store import VectorCandidate
from src.intent_router_contract import map_sector, map_sub_intent
from src.router_config import active_paths


class NpzDenseStore:
    """
    NPZ-dense ANN (cosine via dot product on L2-normalized vectors).
    VectorIndexStore ile aynı search() arayüzü — V2 fallback.
    """

    backend = "npz"

    def __init__(self) -> None:
        paths = active_paths()
        npz = np.load(paths["vectors"])["vectors"].astype(np.float32)
        norms = np.linalg.norm(npz, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        self._vectors = npz / norms

        meta_path = Path(paths["metadata"])
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self._texts: list[str] = list(meta.get("texts") or [])
        self._meta: list[dict] = list(meta.get("meta") or [])
        if len(self._texts) != self._vectors.shape[0]:
            corpus = json.loads(Path(paths["corpus"]).read_text(encoding="utf-8"))
            kayitlar = corpus.get("kayitlar") or []
            self._texts = [
                str(r.get("normalize_mesaj") or r.get("mesaj") or "") for r in kayitlar
            ]
            self._meta = list(kayitlar)
        if self._vectors.shape[1] != EMBEDDING_DIM:
            raise ValueError(f"dim {self._vectors.shape[1]} != {EMBEDDING_DIM}")

    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]:
        if top_k < 1:
            return []
        q = np.asarray(query_embedding, dtype=np.float32).reshape(-1)
        q = q / max(float(np.linalg.norm(q)), 1e-12)
        sims = self._vectors @ q
        k = min(top_k, len(sims))
        idx = np.argpartition(-sims, k - 1)[:k]
        idx = idx[np.argsort(-sims[idx])]
        out: list[VectorCandidate] = []
        for i in idx.tolist():
            m = self._meta[i] if i < len(self._meta) else {}
            sektor_tr = m.get("beklenen_sektor") or ""
            sec = map_sector(str(sektor_tr))
            if sector and sec != sector:
                continue
            text = self._texts[i] if i < len(self._texts) else ""
            sub = map_sub_intent(sec, text) if sec != "ood" else "ood.none"
            score = float(sims[i])
            out.append(
                VectorCandidate(
                    id=int(i),
                    source_id=str(m.get("id") or i),
                    sector=sec,
                    sub_intent=sub,
                    text_content=text,
                    distance=round(max(0.0, 1.0 - score), 6),
                    score=round(score, 6),
                )
            )
            if len(out) >= top_k:
                break
        return out
