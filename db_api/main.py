"""
Chatbot HTTP — yalnızca DB kurgusunun zorunlu kıldığı uçlar.

  POST /api/chat      → reply + url (intents) + session_id
  GET  /api/messages  → role + content + created_at
  GET  /api/health    → ayakta mı (opsiyonel)

  uvicorn db_api.main:app --host 127.0.0.1 --port 8001
  python -m db_api.seed_cli
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from db_api.routers import chat, conversations, health

app = FastAPI(
    title="Chatbot Bilgi Merkezi — Chat API",
    description=(
        "Chatbot-only (v6 şema).\n\n"
        "- `POST /api/chat` — mesaj → cevap + `intents.url` + `session_id`\n"
        "- `GET /api/messages` — `messages` geçmişi\n"
        "- `GET /api/health` — durum\n\n"
        "Seed: `python -m db_api.seed_cli`"
    ),
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__, "path": str(request.url.path)},
    )


API = "/api"
app.include_router(health.router, prefix=API)
app.include_router(chat.router, prefix=API)
app.include_router(conversations.router, prefix=API)


@app.get("/", tags=["health"])
def root():
    return {
        "service": "chatbot-chat-api",
        "version": "2.2.0",
        "post": "POST /api/chat  {message, session_id?}",
        "get": "GET /api/messages?session_id=",
        "health": "GET /api/health",
        "seed": "python -m db_api.seed_cli",
    }
