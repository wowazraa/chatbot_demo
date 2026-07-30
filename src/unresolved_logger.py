"""FB / UNCERTAIN sorguları — aktif öğrenme günlüğü."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_DEFAULT_LOG = Path(__file__).resolve().parents[1] / "logs" / "unresolved_queries.json"


def log_unresolved_query(
    query: str,
    *,
    top_candidates: list[dict[str, Any]] | None = None,
    skor: float | None = None,
    mod: str = "FB",
    path: Path | None = None,
) -> None:
    """Sektör Belirsiz kararlarını JSONL-benzeri diziye ekler (thread-safe)."""
    log_path = path or _DEFAULT_LOG
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "mod": mod,
        "skor": skor,
        "top_candidates": [
            {
                "text": (c.get("text") or "")[:160],
                "sector": c.get("sector"),
                "sub_intent": c.get("sub_intent"),
                "initial_score": c.get("initial_score"),
                "reranker_score": c.get("reranker_score"),
                "final_score": c.get("final_score"),
            }
            for c in (top_candidates or [])[:3]
        ],
    }
    with _LOCK:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []
        if log_path.is_file():
            try:
                rows = json.loads(log_path.read_text(encoding="utf-8"))
                if not isinstance(rows, list):
                    rows = []
            except Exception:
                rows = []
        rows.append(entry)
        # Dosya şişmesin
        if len(rows) > 5000:
            rows = rows[-5000:]
        log_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
