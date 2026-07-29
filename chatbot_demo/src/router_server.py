"""
B2B Intent Router - Production Server
Baseline Architecture: BGE-M3 + Strict Regex Guardrails
Threshold: 0.65 with Regex Fallback Strategy
"""
import sys, os, logging, re, time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, ".")
from src.embedder import get_embedder
from src.k1_guardrails import (
    DECISION_THRESHOLD,
    SECTOR_MAP,
    STRICT_SECTOR_REGEX,
    check_ood_reject,
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
CONFIG = {
    "model": "BGE-M3",
    "threshold": DECISION_THRESHOLD,
    "regex_fallback_enabled": True,
    "max_latency_ms": 30,
    "strict_mode": True
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. STRICT REGEX PATTERNS (Guardrails)
# Kaynak: src.k1_guardrails (router_server.py + v2_pipeline.py ortak kaynağı)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 3. PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────
class RouterRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="User query text")
    request_id: Optional[str] = Field(None, description="Optional request ID for tracking")

class RouterResponse(BaseModel):
    accepted: bool
    predicted_sector: Optional[str]
    confidence_score: float
    regex_matched: bool
    decision_reason: str
    latency_ms: float
    request_id: Optional[str]

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    threshold: float
    uptime_seconds: float

# ─────────────────────────────────────────────────────────────────────────────
# 4. SECTOR MAPPING — src.k1_guardrails.SECTOR_MAP (import edildi)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 5. ROUTER LOGIC
# ─────────────────────────────────────────────────────────────────────────────
class B2BIntentRouter:
    """Production B2B Intent Router with BGE-M3 + Regex Guardrails."""
    
    def __init__(self):
        self.embedder = None
        self.start_time = time.time()
        self._load_model()
    
    def _load_model(self):
        """Load BGE-M3 embedder."""
        try:
            logger.info("Loading BGE-M3 embedder...")
            self.embedder = get_embedder()
            logger.info("BGE-M3 embedder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedder: {e}")
            raise
    
    def check_regex_match(self, query: str, predicted_sector: str) -> bool:
        """Check if query matches strict sector regex pattern."""
        if predicted_sector not in STRICT_SECTOR_REGEX:
            return False
        return bool(STRICT_SECTOR_REGEX[predicted_sector].search(query.lower()))
    
    def check_any_regex_match(self, query: str) -> bool:
        """Check if query matches any sector regex pattern."""
        for pattern in STRICT_SECTOR_REGEX.values():
            if pattern.search(query.lower()):
                return True
        return False

    def route(self, query: str) -> Tuple[bool, Optional[str], float, bool, str]:
        """
        Route query using K1 Regex fast-path first, then BGE-M3 score.

        Decision:
          IF   K1_Regex_Match (sector)    -> ACCEPT (confidence=1.00, no BGE call)
          ELIF OOD_Fast_Reject (B2C/chat) -> REJECT (no BGE call)
          ELIF BGE_M3_Raw_Score >= 0.65   -> ACCEPT
          ELSE                            -> REJECT

        Returns:
            (accepted, predicted_sector, confidence_score, regex_matched, decision_reason)
        """
        start_time = time.perf_counter()

        # K1 Regex fast-path — eşleşirse BGE-M3'e hiç gidilmez (<5ms hedefi)
        for sector, pattern in STRICT_SECTOR_REGEX.items():
            if pattern.search(query.lower()):
                latency = (time.perf_counter() - start_time) * 1000
                reason = f"K1 regex fast-path match (sector: {sector})"
                if latency > CONFIG["max_latency_ms"]:
                    logger.warning(f"High latency: {latency:.2f}ms for query: {query[:50]}")
                return True, sector, 1.0, True, reason

        # OOD Fast-Reject — B2C/chit-chat guardrail; eşleşirse BGE-M3'e hiç gidilmez
        if check_ood_reject(query):
            latency = (time.perf_counter() - start_time) * 1000
            reason = "OOD fast-reject guardrail match (B2C/chit-chat)"
            if latency > CONFIG["max_latency_ms"]:
                logger.warning(f"High latency: {latency:.2f}ms for query: {query[:50]}")
            return False, None, 0.0, False, reason

        # Get BGE-M3 prediction (regex guardrail eşleşmedi)
        hits = self.embedder.find_top_k_hybrid(query, k=1, alpha=0.5)

        if not hits:
            latency = (time.perf_counter() - start_time) * 1000
            return False, None, 0.0, False, "No matches found"

        best = hits[0]
        score = float(best.score)
        meta = (best.metadata or {}).get("beklenen_sektor") or ""
        predicted_sector = SECTOR_MAP.get(str(meta).strip().lower(), "ood")

        # Decision Logic: BGE_M3_Raw_Score >= 0.65 -> ACCEPT, else REJECT
        threshold = CONFIG["threshold"]

        if score >= threshold:
            decision = True
            reason = f"Score {score:.3f} >= threshold {threshold}"
        else:
            decision = False
            reason = f"Score {score:.3f} < threshold {threshold} and no regex match"

        latency = (time.perf_counter() - start_time) * 1000

        # Latency check
        if latency > CONFIG["max_latency_ms"]:
            logger.warning(f"High latency: {latency:.2f}ms for query: {query[:50]}")

        return decision, predicted_sector, score, False, reason

# ─────────────────────────────────────────────────────────────────────────────
# 6. FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="B2B Intent Router API",
    description="Production B2B Intent Router with BGE-M3 + Strict Regex Guardrails",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize router
router = None

@app.on_event("startup")
async def startup_event():
    """Initialize router on startup."""
    global router
    logger.info("Starting B2B Intent Router...")
    router = B2BIntentRouter()
    logger.info("B2B Intent Router ready")

@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if router is None:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    return HealthResponse(
        status="healthy",
        model_loaded=router.embedder is not None,
        threshold=CONFIG["threshold"],
        uptime_seconds=time.time() - router.start_time
    )

# Postman chat and route aliases
@app.post("/route", response_model=RouterResponse)
@app.post("/chat")
@app.post("/api/chat")
async def route_query(request: RouterRequest):
    """
    Route a query through the B2B Intent Router.
    
    Returns:
        RouterResponse with acceptance decision and metadata
    """
    if router is None:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    try:
        accepted, predicted_sector, score, regex_matched, reason = router.route(request.query)
        
        # Postman ve genel uyumluluk için hem RouterResponse hem de genişletilmiş verileri dönelim
        return {
            "accepted": accepted,
            "predicted_sector": predicted_sector if accepted else "ood",
            "sektor": predicted_sector if accepted else "ood",
            "confidence_score": score,
            "skor": score,
            "regex_matched": regex_matched,
            "decision_reason": reason,
            "aciklama": reason,
            "latency_ms": 0.0,
            "request_id": request.request_id,
            "response_message": "Yönlendiriliyorsunuz..." if accepted else "Sektör Belirsiz"
        }
    
    except Exception as e:
        logger.error(f"Error routing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/status")
@app.get("/api/status")
@app.get("/messages")
@app.get("/api/messages")
async def get_status_or_messages():
    """Status & messages metrics endpoint for compatibility."""
    if router is None:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    return {
        "status": "healthy",
        "corpus": 1181,
        "bge_aktif": router.embedder is not None,
        "rewriter": "simulated",
        "sektorler": ["saglik", "turizm", "egitim", "bilisim", "eglence"],
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "B2B Intent Router",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": ["/health", "/api/health"],
            "route": ["/route", "/chat", "/api/chat"],
            "status": ["/status", "/api/status", "/messages", "/api/messages"],
            "docs": "/docs"
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# 7. SERVER ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def start_server(host: str = "0.0.0.0", port: int = 8001):
    """Start the production server."""
    logger.info(f"Starting B2B Intent Router on {host}:{port}")
    logger.info(f"Configuration: {CONFIG}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    start_server()
