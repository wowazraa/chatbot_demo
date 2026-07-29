"""
Chatbot Widget Demo Server — Saf Python, ek bağımlılık yok.
Çalıştır:  python demo/server.py
Tarayıcı:  http://localhost:8080
"""
from __future__ import annotations

import os
import sys

# BGE / transformers: TF-Keras 3 cakismasini bastir (diger importlardan ONCE)
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot
from src.chitchat_rules import match_fast_path
from src.frontend import INSPECTOR_DEMO_SCENARIO, serialize_fast_path, serialize_response

print("[server] Chatbot motoru yükleniyor…", flush=True)
BOT = Chatbot()
print(f"[server] Corpus: {BOT.corpus_boyutu()} kayıt hazır.", flush=True)
print(f"[server] Rewriter: {getattr(BOT._rewriter, 'mode', '?')}", flush=True)

HTML_FILE = Path(__file__).parent / "index.html"
PORT      = 8082

# ─────────────────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    # ── GET: HTML sayfasını sun ───────────────────────────────────────────────
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            content = HTML_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type",   "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/status":
            self._json({
                "corpus":    BOT.corpus_boyutu(),
                "bge_aktif": hasattr(BOT, "bge_aktif_mi") and BOT.bge_aktif_mi(),
                "rewriter":  getattr(getattr(BOT, "_rewriter", None), "mode", "simulated"),
                "pipeline":  ["Katman-1 Rule", "LLMRewriter", "Kısaltma", "BGE-M3", "HAFIZA", "FB"],
                "diller":    ["tr", "en"],
                "sektorler": [
                    "sağlık", "turizm", "eğitim", "bilişim", "eğlence", "belirsiz"
                ],
                "min_bge":   getattr(BOT, "MIN_BGE", 0.80),
                "inspector_demo_scenario": INSPECTOR_DEMO_SCENARIO,
            })
        else:
            self.send_response(404)
            self.end_headers()

    # ── POST /api/chat ────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        length  = int(self.headers.get("Content-Length", 0))
        body    = json.loads(self.rfile.read(length) or b"{}")
        message = body.get("message", "").strip()
        session = body.get("session", "").strip() or None

        if not message:
            self._json({"error": "Boş mesaj"}, status=400)
            return

        t0 = time.perf_counter()
        # Katman 1 — chitchat / gibberish / abuse (ML yok)
        fast = match_fast_path(message)
        if fast is not None:
            total_ms = (time.perf_counter() - t0) * 1000
            self._json(
                serialize_fast_path(
                    message,
                    fast,
                    sure_ms=total_ms,
                    execution_time_ms=total_ms,
                    total_latency_ms=total_ms,
                )
            )
            return

        t_exec = time.perf_counter()
        resp = BOT.sor(message, session_id=session)
        # serialize: tek-kanal Top-3 + SmartGate/CE (ikinci BGE yok)
        payload = serialize_response(resp)
            
        exec_ms = (time.perf_counter() - t_exec) * 1000
        total_ms = (time.perf_counter() - t0) * 1000
        # Latency alanlarını tek pakete yaz (serialize içinde CE süresi exec'e dahil)
        payload["execution_time_ms"] = round(exec_ms, 2)
        payload["total_latency_ms"] = round(total_ms, 2)
        payload["sure_ms"] = round(total_ms, 2)
        if isinstance(payload.get("intent_router"), dict):
            payload["intent_router"]["latency_ms"] = int(round(total_ms))
        # FAZ 5: Sektör Belirsiz → aktif öğrenme günlüğü
        if (payload.get("mod") or "").upper() == "FB":
            try:
                from src.unresolved_logger import log_unresolved_query

                log_unresolved_query(
                    message,
                    top_candidates=list(payload.get("top_candidates") or []),
                    skor=payload.get("skor"),
                    mod="FB",
                )
            except Exception as exc:
                print(f"[server] unresolved log skip: {exc}", flush=True)
        self._json(payload)

    # ── OPTIONS: CORS pre-flight ──────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ── Yardımcılar ──────────────────────────────────────────────────────────
    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        print(f"  [{self.address_string()}] {fmt % args}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()

    print("-" * 50, flush=True)
    print("   Chatbot Widget Demo Server (Allintos / OmniIntent)", flush=True)
    print(f"   Yerel Erişim: http://127.0.0.1:{PORT}", flush=True)
    print(f"   Ağdaki Diğer Cihazlar: http://{IP}:{PORT}", flush=True)
    print(f"   Corpus: {BOT.corpus_boyutu()} kayit hazır.", flush=True)
    print("   Durdurmak icin: Ctrl+C", flush=True)
    print("-" * 50, flush=True)

    # Windows'ta çift bind (SO_REUSEADDR) ERR_EMPTY_RESPONSE üretir — tek listener zorla
    class _ExclusiveHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = False

        def server_bind(self):
            import socket

            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

    try:
        server = _ExclusiveHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as exc:
        print(
            f"[server] Port {PORT} kullanımda veya bağlanamadı: {exc}\n"
            f"  Çözüm:  Get-NetTCPConnection -LocalPort {PORT} | % {{ Stop-Process -Id $_.OwningProcess -Force }}",
            flush=True,
        )
        raise SystemExit(1) from exc

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Kapatıldı.", flush=True)
