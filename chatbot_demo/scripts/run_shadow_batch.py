"""30 sorgu gölge-mod batch — vector_index (pipeline) vs Sinem qa_embeddings.

  python scripts/run_shadow_batch.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.services.pipeline_service import V2IntentPipeline
from app.services.shadow_read_service import LOG_PATH, run_shadow_compare_sync
from scratch.sector_robustness_sweep import CASES


def main() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")

    pipe = V2IntentPipeline()
    results: list[dict] = []

    for case in CASES:
        q = case["q"]
        r = pipe.run(q, session_id=None)
        if r.status == "INFO":
            continue
        entry = run_shadow_compare_sync(
            query=q,
            local_sector=r.sector,
            local_status=r.status,
            local_confidence=float(r.confidence_score),
            local_layer=r.layer,
        )
        results.append(entry)

    comparable = [e for e in results if e.get("remote_top1_sector") is not None and e.get("error") is None]
    empty_remote = [e for e in results if e.get("remote_count") == 0 and not e.get("error")]
    errors = [e for e in results if e.get("error")]
    matches = sum(1 for e in comparable if e.get("sectors_match") is True)
    mismatches = sum(1 for e in comparable if e.get("sectors_match") is False)

    summary = {
        "total_shadow_runs": len(results),
        "skipped_kurumsal_info": len(CASES) - len(results),
        "comparable_with_remote_top1": len(comparable),
        "top1_sector_match": matches,
        "top1_sector_mismatch": mismatches,
        "match_rate_pct": round(100.0 * matches / len(comparable), 1) if comparable else 0.0,
        "empty_remote_results": len(empty_remote),
        "errors": len(errors),
    }

    out = ROOT / "scratch" / "shadow_batch_summary.json"
    out.write_text(
        json.dumps({"summary": summary, "samples": results[:5]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Log: {LOG_PATH}")
    print(f"Summary: {out}")

    if errors:
        print("\nErrors:")
        for e in errors[:3]:
            print(" ", e.get("query", "")[:50], e.get("error"))


if __name__ == "__main__":
    main()
