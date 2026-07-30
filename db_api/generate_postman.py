"""Chatbot Chat API — session_id ilk POST'ta null, sonra sabitlenir."""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "postman_collection.json"
ENV = Path(__file__).resolve().parent / "postman_environment.json"
BASE = "{{base_url}}"


def req(name, method, path, body=None, tests=None, prereq=None):
    item: dict = {
        "name": name,
        "request": {
            "method": method,
            "header": [{"key": "Content-Type", "value": "application/json"}] if body is not None else [],
            "url": f"{BASE}{path}",
        },
    }
    if body is not None:
        raw = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=2)
        item["request"]["body"] = {"mode": "raw", "raw": raw}
    events = []
    if prereq:
        events.append({"listen": "prerequest", "script": {"exec": prereq, "type": "text/javascript"}})
    if tests:
        events.append({"listen": "test", "script": {"exec": tests, "type": "text/javascript"}})
    if events:
        item["event"] = events
    return item


# Body: session_id placeholder — prerequest null veya sayı yazar
CHAT_BODY = """{
  "message": "Kardiyoloji randevusu almak istiyorum",
  "session_id": {{session_id_json}},
  "user_identifier": "postman-user"
}"""

SAVE_SESSION = [
    "if (pm.response.code === 200) {",
    "  const j = pm.response.json();",
    "  if (j.session_id != null) {",
    "    pm.collectionVariables.set('session_id', String(j.session_id));",
    "  }",
    "}",
]

# İlk istekte boş → null; doluysa sayı (tırnaksız JSON)
PREREQ_SESSION = [
    "let s = pm.collectionVariables.get('session_id');",
    "if (!s || s === '' || s === 'null') {",
    "  pm.collectionVariables.set('session_id_json', 'null');",
    "} else {",
    "  pm.collectionVariables.set('session_id_json', String(s));",
    "}",
]

collection = {
    "info": {
        "name": "Chatbot Bilgi Merkezi — Chat API (v2.2)",
        "description": (
            "POST chat: ilk mesajda session_id=null, sonra aynı id ile devam.\n"
            "Environment'ta session_id tutma — Collection Variables kullan.\n\n"
            "uvicorn db_api.main:app --host 127.0.0.1 --port 8001\n"
            "python -m db_api.seed_cli"
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "base_url", "value": "http://127.0.0.1:8001"},
        {"key": "session_id", "value": ""},
        {"key": "session_id_json", "value": "null"},
    ],
    "item": [
        {
            "name": "Chatbot",
            "item": [
                req("1 GET health", "GET", "/api/health"),
                req(
                    "2 POST chat",
                    "POST",
                    "/api/chat",
                    CHAT_BODY,
                    tests=SAVE_SESSION,
                    prereq=PREREQ_SESSION,
                ),
                req(
                    "3 GET messages",
                    "GET",
                    "/api/messages?session_id={{session_id}}&limit=50&offset=0",
                ),
            ],
        },
    ],
}

env = {
    "id": "chatbot-chat-api-env-v22",
    "name": "Chatbot Chat API — Local 8001",
    "values": [
        {"key": "base_url", "value": "http://127.0.0.1:8001", "enabled": True},
        # session_id bilerek YOK — collection variable kullanılsın
    ],
    "_postman_variable_scope": "environment",
}

OUT.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
ENV.write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Wrote {ENV}")
