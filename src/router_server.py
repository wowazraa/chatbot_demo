"""
B2B Intent Router - Production Server
Baseline Architecture: BGE-M3 + Strict Regex Guardrails
Threshold: 0.65 with Regex Fallback Strategy
"""
import sys, os, logging, re, time
import uuid
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
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
from dotenv import load_dotenv
import psycopg2

load_dotenv()

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

# Session management models
class SessionCreate(BaseModel):
    user_id: Optional[str] = None
    sector: Optional[str] = None
    metadata: Optional[Dict] = None

class SessionResponse(BaseModel):
    session_id: str
    user_id: Optional[str]
    sector: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict

class MessageCreate(BaseModel):
    session_id: str
    role: str = Field(..., description="user, assistant, or system")
    content: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict] = None

class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    intent: Optional[str]
    confidence: Optional[float]
    created_at: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=500)
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    user_message: str
    bot_response: str
    predicted_sector: Optional[str]
    confidence: float
    messages: List[MessageResponse]

# ─────────────────────────────────────────────────────────────────────────────
# 4. SECTOR MAPPING — src.k1_guardrails.SECTOR_MAP (import edildi)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 5. DATABASE HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def get_db_connection():
    """Get PostgreSQL database connection."""
    db_url = os.getenv('DATABASE_URL').replace('postgresql+psycopg2://', 'postgresql://')
    return psycopg2.connect(db_url)

def create_session(user_id: Optional[str] = None, sector: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
    """Create a new chat session and return session_id."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        session_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else '{}'
        
        cursor.execute(
            "INSERT INTO chat_sessions (id, user_id, sector, metadata) VALUES (%s, %s, %s, %s) RETURNING id",
            (session_id, user_id, sector, metadata_json)
        )
        conn.commit()
        return session_id
    finally:
        conn.close()

def get_session(session_id: str) -> Optional[Dict]:
    """Get session by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, sector, created_at, updated_at, metadata FROM chat_sessions WHERE id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "session_id": str(row[0]),
                "user_id": row[1],
                "sector": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": row[4].isoformat() if row[4] else None,
                "metadata": row[5]
            }
        return None
    finally:
        conn.close()

def add_message(session_id: str, role: str, content: str, intent: Optional[str] = None, confidence: Optional[float] = None, metadata: Optional[Dict] = None) -> int:
    """Add a message to a session and return message ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata) if metadata else '{}'
        
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content, intent, confidence, metadata) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (session_id, role, content, intent, confidence, metadata_json)
        )
        message_id = cursor.fetchone()[0]
        
        # Update session updated_at
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
            (session_id,)
        )
        
        conn.commit()
        return message_id
    finally:
        conn.close()

def get_session_messages(session_id: str) -> List[Dict]:
    """Get all messages for a session."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_id, role, content, intent, confidence, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "session_id": str(row[1]),
                "role": row[2],
                "content": row[3],
                "intent": row[4],
                "confidence": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            }
            for row in rows
        ]
    finally:
        conn.close()

import json

# ─────────────────────────────────────────────────────────────────────────────
# 6. ROUTER LOGIC
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
            "session": ["/api/sessions", "/api/sessions/{session_id}", "/api/sessions/{session_id}/messages"],
            "docs": "/docs"
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# 8. SESSION MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/sessions", response_model=SessionResponse)
async def create_chat_session(session_data: SessionCreate):
    """Create a new chat session."""
    try:
        session_id = create_session(
            user_id=session_data.user_id,
            sector=session_data.sector,
            metadata=session_data.metadata
        )
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")
        return SessionResponse(**session)
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(session_id: str):
    """Get a chat session by ID."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionResponse(**session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages_endpoint(session_id: str):
    """Get all messages for a session."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = get_session_messages(session_id)
        return [MessageResponse(**msg) for msg in messages]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/session", response_model=ChatResponse)
async def chat_with_session(chat_request: ChatRequest):
    """Chat with session management."""
    if router is None:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    try:
        # Get or create session
        session_id = chat_request.session_id
        if not session_id:
            # Create new session
            session_id = create_session(user_id=chat_request.user_id)
        
        # Route the user message
        accepted, predicted_sector, score, regex_matched, reason = router.route(chat_request.message)
        
        # Generate bot response
        if accepted:
            bot_response = f"Talebiniz {predicted_sector} sektörüyle ilişkilendirildi. Size nasıl yardımcı olabilirim?"
        else:
            bot_response = "Sektör belirlenemedi. Lütfen daha spesifik bir talep belirtin."
        
        # Add user message to session
        add_message(
            session_id=session_id,
            role="user",
            content=chat_request.message,
            intent=predicted_sector if accepted else None,
            confidence=score
        )
        
        # Add bot response to session
        add_message(
            session_id=session_id,
            role="assistant",
            content=bot_response,
            intent=predicted_sector if accepted else None,
            confidence=score
        )
        
        # Get all messages for the session
        messages = get_session_messages(session_id)
        
        return ChatResponse(
            session_id=session_id,
            user_message=chat_request.message,
            bot_response=bot_response,
            predicted_sector=predicted_sector if accepted else None,
            confidence=score,
            messages=[MessageResponse(**msg) for msg in messages]
        )
    
    except Exception as e:
        logger.error(f"Error in chat with session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
