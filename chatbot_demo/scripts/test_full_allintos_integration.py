"""Tam Allintos entegrasyon smoke test."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import use_allintos_chat_db
from app.db.allintos_db import fetch_readonly
from app.db.database import get_chat_db
from app.services.intent_url_service import refresh_intent_url_cache, resolve_intent_url
from app.services.k0_corporate_info import invalidate_k0_records_cache, try_k0_corporate_info
from app.services.session_service import persist_chat_turn
from app.schemas import ChatLogRequest
from app.db.allintos_knowledge_store import search_corporate_knowledge
from app.services.similarity_service import SimilarityService


def test_intent_urls() -> bool:
    refresh_intent_url_cache()
    url = resolve_intent_url("saglik", "SUCCESS")
    ok = bool(url and url.startswith("http"))
    print(f"  intent_url saglik: {url} -> {'OK' if ok else 'FAIL'}")
    return ok


def test_chat_persist() -> bool:
    if not use_allintos_chat_db():
        print("  chat_persist SKIP (ALLINTOS_CHAT_DB=local)")
        return True
    db = next(get_chat_db())
    try:
        uid = f"integration-test-{uuid.uuid4().hex[:8]}"
        saved = persist_chat_turn(
            db,
            ChatLogRequest(
                user_identifier=uid,
                session_name="integration-smoke",
                user_message="test mesaji",
                bot_message="test cevabi",
                intent="test",
                layer_hit="test",
                confidence=1.0,
                response_ms=1,
                source="integration_test",
            ),
        )
        cnt = fetch_readonly("SELECT COUNT(*) FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE session_id = %s)", (saved.session_id,))[0][0]
        ok = cnt >= 2
        print(f"  chat_persist session_id={saved.session_id} messages={cnt} -> {'OK' if ok else 'FAIL'}")
        return ok
    finally:
        db.close()


def test_knowledge_search() -> bool:
    svc = SimilarityService(top_k=1)
    vec = svc.embed_query("DDX hakkında bilgi")
    hits = search_corporate_knowledge(vec, top_k=3)
    ok = len(hits) >= 1 and bool((hits[0].record_meta or {}).get("cevap"))
    print(f"  knowledge_search top1_score={hits[0].score if hits else 0:.3f} -> {'OK' if ok else 'FAIL'}")
    return ok


def test_k0() -> bool:
    invalidate_k0_records_cache()
    hit = try_k0_corporate_info("TUBITAK nedir")
    ok = hit is not None and hit.get("k0_source") == "allintos"
    print(f"  k0 allintos: {'OK' if ok else 'FAIL'}")
    return ok


def main() -> None:
    print("=== FULL INTEGRATION SMOKE ===")
    results = [
        test_intent_urls(),
        test_k0(),
        test_knowledge_search(),
        test_chat_persist(),
    ]
    passed = sum(results)
    print(f"\nSonuc: {passed}/{len(results)}")
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
