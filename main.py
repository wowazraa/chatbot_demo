"""
Chatbot Bilgi Merkezi — uygulama giriş noktası.

  uvicorn main:app --host 127.0.0.1 --port 8082
  python -m scripts.seed_cli
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import admin_qa, chat, conversations, health

app = FastAPI(
    title="Chatbot Bilgi Merkezi — Chat API",
    description=(
        "B2B Intent Router (v6 şema).\n\n"
        "- `POST /api/chat` — mesaj → cevap + intent URL + session_id\n"
        "- `GET /api/messages` — mesaj geçmişi\n"
        "- `GET /api/health` — durum\n"
        "- `POST /api/admin/add_qa` — soru ekleme ve augmentasyon\n\n"
        "Yapı: app/api · app/services · app/db · static/"
    ),
    version="3.0.0",
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
app.include_router(admin_qa.router, prefix=API)


@app.get("/", tags=["health"])
def root():
    index_path = _ROOT / "static" / "widget_test.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return {"error": "widget_test.html not found"}


app.mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static")
# Geriye dönük widget yolu
app.mount("/demo", StaticFiles(directory=str(_ROOT / "static")), name="demo")
