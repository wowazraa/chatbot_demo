"""Örnek veriyi CLI ile yükle.

  cd chatbot_demo
  python -m scripts.seed_cli
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db.database import SessionLocal
from app.schemas import ChatLogRequest
from app.services.session_service import persist_chat_turn
from scripts.seed import _run_seed


def main() -> None:
    db = SessionLocal()
    try:
        result = _run_seed(db)
        sample = persist_chat_turn(
            db,
            ChatLogRequest(
                user_identifier="seed-user",
                session_name="seed-session",
                session_id=result.sample_session_id,
                user_message="Hastane randevu sistemi arıyoruz",
                bot_message="Sağlık olarak anladım.",
                intent="health_appointment",
                layer_hit="K2",
                confidence=0.95,
                response_ms=12,
                source="seed",
            ),
        )
        out = result.model_dump()
        out["sample_messages"] = sample.model_dump()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        print("OK — seed + örnek mesajlar yazıldı", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    main()
