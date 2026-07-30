from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from db_api.bridge import EMBEDDING_DIM, USE_PGVECTOR, QaEmbedding, get_db
from db_api.common import Page, not_found, paginate
from db_api.schemas import QaOut, QaSearchHit, QaSearchRequest

router = APIRouter(prefix="/qa", tags=["qa_embeddings"])


def _cosine_distance(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-12
    nb = math.sqrt(sum(x * x for x in b)) or 1e-12
    return 1.0 - (dot / (na * nb))


@router.get("", response_model=Page)
def list_qa(
    intent_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(QaEmbedding).order_by(QaEmbedding.id)
    if intent_id is not None:
        q = q.filter(QaEmbedding.intent_id == intent_id)
    items, total = paginate(q, limit, offset)
    return Page(items=[QaOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)


@router.get("/{qa_id}", response_model=QaOut)
def get_qa(qa_id: int, db: Session = Depends(get_db)):
    row = db.get(QaEmbedding, qa_id)
    if not row:
        raise not_found("qa")
    return row


@router.post("/search", response_model=list[QaSearchHit])
def search_qa(body: QaSearchRequest, db: Session = Depends(get_db)):
    if len(body.embedding) != EMBEDDING_DIM:
        raise HTTPException(400, f"embedding must be length {EMBEDDING_DIM}")

    if USE_PGVECTOR:
        vec_literal = "[" + ",".join(str(float(x)) for x in body.embedding) + "]"
        sql = """
            SELECT id, question, answer, intent_id,
                   (embedding <=> CAST(:emb AS vector)) AS distance
            FROM qa_embeddings
            WHERE (:intent_id IS NULL OR intent_id = :intent_id)
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :lim
        """
        rows = db.execute(
            text(sql),
            {"emb": vec_literal, "intent_id": body.intent_id, "lim": body.limit},
        ).mappings().all()
        return [QaSearchHit(**dict(r)) for r in rows]

    q = db.query(QaEmbedding)
    if body.intent_id is not None:
        q = q.filter(QaEmbedding.intent_id == body.intent_id)
    scored = [
        QaSearchHit(
            id=row.id,
            question=row.question,
            answer=row.answer,
            intent_id=row.intent_id,
            distance=_cosine_distance(body.embedding, list(row.embedding)),
        )
        for row in q.all()
    ]
    scored.sort(key=lambda h: h.distance)
    return scored[: body.limit]
