"""Gölge mod — Sinem qa_embeddings vs yerel pipeline (kullanıcıya yansımaz)."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import load_dotenv
from app.core.intent_mapping import SEKTOR_TO_INTENT
from app.db.allintos_db import (
    CANONICAL_SERVICE_INTENT_CODES,
    SERVICE_SECTORS,
    fetch_readonly,
    get_allintos_readonly_url,
    is_allintos_readonly_configured,
    mask_db_url,
)

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "scratch" / "shadow_read_comparison.log"

_INTENT_CODE_TO_SECTOR = {
    SEKTOR_TO_INTENT[s]: s for s in SERVICE_SECTORS
}

_shadow_lock = threading.Lock()


def shadow_read_enabled() -> bool:
    flag = (os.getenv("SHADOW_READ_ENABLED") or "true").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return is_allintos_readonly_configured()


def _append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with _shadow_lock:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _search_allintos_qa(
    query_embedding: np.ndarray,
    *,
    top_k: int = 50,
) -> list[dict[str, Any]]:
    lit = "[" + ",".join(f"{float(x):.8f}" for x in query_embedding.reshape(-1).tolist()) + "]"
    sql = """
        SELECT q.id, q.question, i.intent_code,
               (q.embedding <=> CAST(%s AS vector)) AS distance
        FROM qa_embeddings q
        JOIN intents i ON q.intent_id = i.id
        WHERE i.intent_code = ANY(%s)
        ORDER BY q.embedding <=> CAST(%s AS vector)
        LIMIT %s
    """
    rows = fetch_readonly(sql, (lit, list(CANONICAL_SERVICE_INTENT_CODES), lit, int(top_k)))

    out: list[dict[str, Any]] = []
    for row_id, question, intent_code, distance in rows:
        dist = float(distance)
        sector = _INTENT_CODE_TO_SECTOR.get(str(intent_code), "ood")
        out.append(
            {
                "id": int(row_id),
                "question": question,
                "intent_code": intent_code,
                "sector": sector,
                "distance": round(dist, 6),
                "score": round(max(0.0, 1.0 - dist), 6),
            }
        )
    return out


def _run_shadow_compare(
    *,
    query: str,
    local_sector: str,
    local_status: str,
    local_confidence: float,
    local_layer: str,
    top_k: int,
) -> None:
    t0 = time.perf_counter()
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "local": {
            "sector": local_sector,
            "status": local_status,
            "confidence": local_confidence,
            "layer": local_layer,
        },
        "remote_db": mask_db_url(get_allintos_readonly_url() or ""),
        "remote_top_k": [],
        "remote_top1_sector": None,
        "sectors_match": None,
        "error": None,
        "latency_ms": None,
    }
    try:
        from app.services.embedder import get_embedder

        vec = get_embedder().encode_dense([query])[0]
        remote = _search_allintos_qa(vec, top_k=top_k)
        entry["remote_top_k"] = remote[:5]
        if remote:
            entry["remote_top1_sector"] = remote[0]["sector"]
            entry["sectors_match"] = remote[0]["sector"] == local_sector
        entry["remote_count"] = len(remote)
    except Exception as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
    entry["latency_ms"] = int(round((time.perf_counter() - t0) * 1000))
    _append_log(entry)


def run_shadow_compare_sync(
    *,
    query: str,
    local_sector: str,
    local_status: str,
    local_confidence: float,
    local_layer: str,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Senkron gölge karşılaştırma (batch test / log)."""
    k = top_k if top_k is not None else int(os.getenv("SHADOW_READ_TOP_K", "50"))
    _run_shadow_compare(
        query=query,
        local_sector=local_sector,
        local_status=local_status,
        local_confidence=local_confidence,
        local_layer=local_layer,
        top_k=k,
    )
    if LOG_PATH.exists():
        last = LOG_PATH.read_text(encoding="utf-8").strip().splitlines()[-1]
        return json.loads(last)
    return {"error": "log_missing"}


def maybe_schedule_shadow_read(
    *,
    query: str,
    local_sector: str,
    local_status: str,
    local_confidence: float,
    local_layer: str,
) -> None:
    """
    Arka planda Sinem qa_embeddings araması — yalnız 5 sektör, kurumsal (INFO) hariç.
    Kullanıcı yanıtına dokunmaz.
    """
    if not shadow_read_enabled():
        return
    if local_status == "INFO":
        return
    if local_sector == "info":
        return

    top_k = int(os.getenv("SHADOW_READ_TOP_K", "50"))
    thread = threading.Thread(
        target=_run_shadow_compare,
        kwargs={
            "query": query,
            "local_sector": local_sector,
            "local_status": local_status,
            "local_confidence": local_confidence,
            "local_layer": local_layer,
            "top_k": top_k,
        },
        daemon=True,
        name="shadow-read",
    )
    thread.start()
