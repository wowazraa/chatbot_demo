"""
BGE-M3 Embedding Wrapper (Dense + Sparse Hybrid Version)
=========================================================
BAAI/bge-m3 — dense + sparse multilingual hybrid retrieval
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# FlagEmbedding/transformers Keras 3 cakismasini onle (import ONCE)
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
MODEL_NAME   = "BAAI/bge-m3"
INDEX_FILE   = "embeddings.npz"
META_FILE    = "index_meta.json"
DEFAULT_K    = 5
BATCH_SIZE   = 32


# ---------------------------------------------------------------------------
# Yardımcı: model yükleme (lazy, bir kez)
# ---------------------------------------------------------------------------
_model = None


def _get_model():
    global _model
    if _model is None:
        os.environ["USE_TF"] = "0"
        os.environ["TRANSFORMERS_NO_TF"] = "1"
        try:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore
        except Exception as e:
            raise ImportError(
                "FlagEmbedding / BGE-M3 yuklenemedi. "
                "Dene: pip install FlagEmbedding tf-keras\n"
                f"Detay: {e}"
            ) from e
        from src.models.torch_runtime import configure_torch_threads

        n_threads = configure_torch_threads(4)
        print(f"[BGEEmbedder] Model yükleniyor: {MODEL_NAME} (threads={n_threads}) ...")
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = BGEM3FlagModel(MODEL_NAME, device=device, use_fp16=(device == "cuda"))
        print("[BGEEmbedder] Model hazır.")
    return _model


def _encode_under_inference(model, texts, **kwargs):
    """FlagEmbedding encode — torch.inference_mode altında."""
    import torch

    with torch.inference_mode():
        return model.encode(texts, **kwargs)

# ---------------------------------------------------------------------------
# Sonuç veri yapısı
# ---------------------------------------------------------------------------
@dataclass
class EmbedResult:
    idx:      int
    score:    float
    metadata: dict[str, Any]
    text:     str


# ---------------------------------------------------------------------------
# Ana sınıf
# ---------------------------------------------------------------------------
class BGEEmbedder:
    """
    BGE-M3 tabanlı dense + sparse anlamsal benzerlik motoru.
    """

    def __init__(self) -> None:
        self._vectors: np.ndarray | None = None   # (N, D) float32 (dense)
        self._sparse_vectors: list[dict[str, float]] | None = None # list of N dicts (sparse)
        self._texts:   list[str]         = []
        self._meta:    list[dict]        = []

    # ------------------------------------------------------------------
    # Index oluşturma
    # ------------------------------------------------------------------
    def build_index(
        self,
        texts: list[str],
        metadata: list[dict[str, Any]],
        *,
        show_progress: bool = True,
    ) -> None:
        """Tüm corpus'u dense + sparse olarak embed edip index'e ekler."""
        if len(texts) != len(metadata):
            raise ValueError("texts ve metadata aynı uzunlukta olmalı")

        model = _get_model()
        print(f"[BGEEmbedder] {len(texts)} kayıt dense + sparse olarak embed ediliyor (batch={BATCH_SIZE})…")

        out = _encode_under_inference(
            model,
            texts,
            batch_size=BATCH_SIZE,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )

        self._vectors = out["dense_vecs"].astype(np.float32)
        self._sparse_vectors = out["lexical_weights"]
        self._texts   = list(texts)
        self._meta    = list(metadata)
        print(f"[BGEEmbedder] Index hazır: dense {self._vectors.shape}, sparse {len(self._sparse_vectors)}")

    # ------------------------------------------------------------------
    # Kaydet / Yükle
    # ------------------------------------------------------------------
    def save_index(
        self,
        directory: Path,
        *,
        vectors_path: Path | None = None,
        meta_path: Path | None = None,
    ) -> None:
        """Index'i npz + json olarak kaydet."""
        directory.mkdir(parents=True, exist_ok=True)
        npz_path = vectors_path or (directory / INDEX_FILE)
        meta_file = meta_path or (directory / META_FILE)
        np.savez_compressed(npz_path, vectors=self._vectors)

        # float32 tipini standart float'a dönüştür (JSON serialization için)
        serializable_sparse = []
        if self._sparse_vectors:
            for d in self._sparse_vectors:
                serializable_sparse.append({k: float(v) for k, v in d.items()})
        else:
            serializable_sparse = [{} for _ in range(len(self._texts))]

        with meta_file.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "texts": self._texts,
                    "meta": self._meta,
                    "sparse_vectors": serializable_sparse,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"[BGEEmbedder] Index kaydedildi -> {npz_path.name} + {meta_file.name}")

    def load_index(
        self,
        directory: Path,
        *,
        vectors_path: Path | None = None,
        meta_path: Path | None = None,
    ) -> None:
        """Kaydedilmiş index'i yükle (varsayılan veya router_config yolları)."""
        npz_path = vectors_path or (directory / INDEX_FILE)
        meta_file = meta_path or (directory / META_FILE)

        if not npz_path.exists() or not meta_file.exists():
            raise FileNotFoundError(
                f"Index dosyaları bulunamadı:\n  {npz_path}\n  {meta_file}\n"
                "Önce `python scripts/build_index.py` veya "
                "`python scripts/build_clean_index.py` çalıştırın."
            )

        data = np.load(npz_path)
        self._vectors = data["vectors"].astype(np.float32)

        with meta_file.open(encoding="utf-8") as f:
            payload = json.load(f)

        self._texts = payload["texts"]
        self._meta = payload["meta"]
        self._sparse_vectors = payload.get("sparse_vectors")

        # Geriye dönük uyumluluk: eski index formatında sparse yoksa boş oluştur
        if self._sparse_vectors is None:
            self._sparse_vectors = [{} for _ in range(len(self._texts))]

        print(
            f"[BGEEmbedder] Index yüklendi: {self._vectors.shape[0]} kayıt, "
            f"dim={self._vectors.shape[1]} | {npz_path.name}"
        )
    # ------------------------------------------------------------------
    # Hibrit Sorgulama
    # ------------------------------------------------------------------
    def find_top_k_hybrid(
        self,
        query: str,
        k: int = DEFAULT_K,
        alpha: float = 0.5,
    ) -> list[EmbedResult]:
        """Dense ve Sparse skorları birleştirerek Top-K döner."""
        if self._vectors is None or self._sparse_vectors is None:
            raise RuntimeError("Index boş. Önce build_index veya load_index çağırın.")

        model = _get_model()
        out = _encode_under_inference(
            model,
            [query],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )

        q_dense = out["dense_vecs"][0].astype(np.float32)
        q_sparse = dict(out["lexical_weights"][0])

        # Boost specific keywords in query sparse weights
        # Boost specific service keywords and reduce venue keywords to prevent venue-service confusion
        boost_keywords = {
            "saas", "sdk", "lms", "ott", "api", "software", "automation", "portal", 
            "integration", "system", "database", "yazılım", "otomasyon", "sistem", 
            "entegrasyon", "yazilim", "crm", "erp", "hbys", "pacs", "lis",
            "cybersecurity", "cyber", "firewall", "siem", "security",
            "virüs", "virus", "bilgisayar", "temizleme", "hastane", "hasta", "hekim", "klinik",
            "festival", "festivalleri", "biletleme", "etkinlik", "konser", "tiyatro", "organizasyon"
        }
        venue_keywords = {"hotel", "school", "otel", "okul"}
        
        has_service = any(term.lower() in boost_keywords for term in q_sparse)
        
        for term, weight in list(q_sparse.items()):
            term_lower = term.lower()
            if term_lower in boost_keywords:
                q_sparse[term] = weight * 3.0
            elif term_lower in venue_keywords and has_service:
                q_sparse[term] = weight * 0.5

        # 1. Dense Cosine Similarity (dot product)
        dense_scores = (self._vectors @ q_dense).tolist()

        # 2. Sparse Cosine Similarity
        sparse_scores = []
        for d_sparse in self._sparse_vectors:
            common = set(q_sparse.keys()) & set(d_sparse.keys())
            if not common:
                sparse_scores.append(0.0)
                continue

            dot_product = sum(q_sparse[t] * d_sparse[t] for t in common)
            norm_q = math.sqrt(sum(v * v for v in q_sparse.values()))
            norm_d = math.sqrt(sum(v * v for v in d_sparse.values()))

            sim = dot_product / (norm_q * norm_d) if (norm_q > 0.0 and norm_d > 0.0) else 0.0
            sparse_scores.append(sim)

        # 3. Hibrit Skorlama (Dense ve Sparse birleşimi)
        hybrid_scores = [
            alpha * d_s + (1 - alpha) * s_s
            for d_s, s_s in zip(dense_scores, sparse_scores)
        ]

        top_indices = sorted(
            range(len(hybrid_scores)), key=lambda i: hybrid_scores[i], reverse=True
        )[:k]

        return [
            EmbedResult(
                idx=i,
                score=round(hybrid_scores[i], 6),
                metadata=self._meta[i],
                text=self._texts[i],
            )
            for i in top_indices
        ]

    def find_top_k(
        self,
        query: str,
        k: int = DEFAULT_K,
        alpha: float = 0.5,
    ) -> list[EmbedResult]:
        """find_top_k_hybrid'e yönlendirir (geriye dönük uyumluluk için)."""
        return self.find_top_k_hybrid(query, k=k, alpha=alpha)

    def encode_dense(self, texts: list[str]) -> np.ndarray:
        """Metinleri dense BGE vektörüne çevir (N, D), L2-normalize."""
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        model = _get_model()
        out = _encode_under_inference(
            model,
            texts,
            batch_size=min(BATCH_SIZE, max(1, len(texts))),
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        vecs = out["dense_vecs"].astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return vecs / norms

    @staticmethod
    def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        """İki L2-normalize vektör için cosine (dot)."""
        return float(np.dot(a, b))

    # ------------------------------------------------------------------
    # Yardımcı
    # ------------------------------------------------------------------
    def size(self) -> int:
        return len(self._texts)

    def is_ready(self) -> bool:
        return self._vectors is not None and len(self._texts) > 0


# ---------------------------------------------------------------------------
# Singleton (chatbot.py tarafından kullanılır)
# ---------------------------------------------------------------------------
_embedder_instance: BGEEmbedder | None = None
_embedder_key: tuple[str, str] | None = None


def reset_embedder() -> None:
    """Config degisince singleton'i dusur (test / yol guncelleme)."""
    global _embedder_instance, _embedder_key
    _embedder_instance = None
    _embedder_key = None


def get_embedder(index_dir: Path | None = None) -> BGEEmbedder:
    """Process başına bir kez yükle; yollar config/router_config.json'dan."""
    global _embedder_instance, _embedder_key

    vectors_path: Path | None = None
    meta_path: Path | None = None
    directory = index_dir
    try:
        from src.router_config import active_paths

        paths = active_paths()
        directory = directory or paths["index_dir"]  # type: ignore[assignment]
        vectors_path = paths["vectors"]  # type: ignore[assignment]
        meta_path = paths["metadata"]  # type: ignore[assignment]
        key = (str(vectors_path), str(meta_path))
    except Exception:
        directory = directory or Path("data/processed")
        key = (str(directory / INDEX_FILE), str(directory / META_FILE))

    if (
        _embedder_instance is None
        or not _embedder_instance.is_ready()
        or _embedder_key != key
    ):
        _embedder_instance = BGEEmbedder()
        _embedder_instance.load_index(
            directory,  # type: ignore[arg-type]
            vectors_path=vectors_path,
            meta_path=meta_path,
        )
        _embedder_key = key
    return _embedder_instance

