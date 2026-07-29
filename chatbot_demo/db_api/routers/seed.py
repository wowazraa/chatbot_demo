"""Demo seed — olması gereken örnek veriyi upsert eder; demo çöpünü temizler.

TRUNCATE / reset YOK — mevcut doğru kayıtlar kalır, eksikler tamamlanır,
Türkçe isimler düzeltilir, Postman deneme kayıtları (demo_tmp vb.) silinir.
"""

from __future__ import annotations

from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db_api.bridge import EMBEDDING_DIM, AdminUser, Blog, ChatSession, Company, Intent, QaEmbedding, Sector, get_db
from db_api.schemas import SeedResponse

router = APIRouter(prefix="/seed", tags=["seed"])

# Postman Create denemelerinden kalan anahtarlar
_JUNK_SECTOR_KEYS = ("demo_tmp",)
_JUNK_INTENT_CODES = ("tmp_intent",)
_JUNK_COMPANY_NAMES = ("Temp Co Postman", "Temp Co Updated")
_JUNK_BLOG_SLUGS = ("postman-tmp",)
_JUNK_ADMIN_USERNAMES = ("editor_tmp",)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _upsert_sector(db: Session, key: str, tr: str, en: str) -> Sector:
    row = db.query(Sector).filter_by(sector_key=key).first()
    if row:
        row.sector_name_tr = tr
        row.sector_name_en = en
        return row
    row = Sector(sector_key=key, sector_name_tr=tr, sector_name_en=en)
    db.add(row)
    db.flush()
    return row


def _upsert_intent(db: Session, code: str, url: str, desc: str) -> Intent:
    row = db.query(Intent).filter_by(intent_code=code).first()
    if row:
        row.url = url
        row.description = desc
        return row
    row = Intent(intent_code=code, url=url, description=desc)
    db.add(row)
    db.flush()
    return row


def _cleanup_junk(db: Session) -> None:
    for key in _JUNK_SECTOR_KEYS:
        row = db.query(Sector).filter_by(sector_key=key).first()
        if row:
            db.delete(row)
    for code in _JUNK_INTENT_CODES:
        row = db.query(Intent).filter_by(intent_code=code).first()
        if row:
            db.delete(row)
    for name in _JUNK_COMPANY_NAMES:
        row = db.query(Company).filter_by(company_name=name).first()
        if row:
            db.delete(row)
    for slug in _JUNK_BLOG_SLUGS:
        row = db.query(Blog).filter_by(slug=slug).first()
        if row:
            db.delete(row)
    for username in _JUNK_ADMIN_USERNAMES:
        row = db.query(AdminUser).filter_by(username=username).first()
        if row:
            db.delete(row)
    db.flush()


def _run_seed(db: Session) -> SeedResponse:
    _cleanup_junk(db)

    sectors = [
        ("health", "Sağlık", "Health"),
        ("tourism", "Turizm", "Tourism"),
        ("defense", "Savunma", "Defense"),
        ("education", "Eğitim", "Education"),
    ]
    n_sec = 0
    sector_map: dict[str, Sector] = {}
    for key, tr, en in sectors:
        sector_map[key] = _upsert_sector(db, key, tr, en)
        n_sec += 1

    intents = [
        ("health_appointment", "https://example.com/forms/health", "Sağlık randevu formu"),
        ("tourism_hotel", "https://example.com/forms/tourism", "Turizm konaklama formu"),
        ("defense_inquiry", "https://example.com/forms/defense", "Savunma talep formu"),
        ("education_enrollment", "https://example.com/forms/education", "Eğitim kayıt formu"),
        ("sector_form_request", "https://example.com/forms/sector", "Genel sektör formu"),
    ]
    n_int = 0
    intent_map: dict[str, Intent] = {}
    for code, url, desc in intents:
        intent_map[code] = _upsert_intent(db, code, url, desc)
        n_int += 1

    companies = [
        ("Acme Sağlık A.Ş.", "health"),
        ("Gamma Turizm A.Ş.", "tourism"),
        ("Delta Savunma Ltd.", "defense"),
        ("Epsilon Eğitim A.Ş.", "education"),
    ]
    n_co = 0
    for name, sk in companies:
        sid = sector_map[sk].id
        row = db.query(Company).filter_by(company_name=name).first()
        if row:
            row.sector_id = sid
        else:
            # Aynı sektördeki eski/bozuk isimli seed şirketini düzelt
            prefix = name.split()[0]
            legacy = (
                db.query(Company)
                .filter(Company.sector_id == sid)
                .filter(Company.company_name.like(f"{prefix}%"))
                .first()
            )
            if legacy:
                legacy.company_name = name
                legacy.sector_id = sid
            else:
                db.add(Company(company_name=name, sector_id=sid))
        n_co += 1

    admin = db.query(AdminUser).filter_by(username="admin").first()
    admin_upserted = False
    if not admin:
        admin = AdminUser(
            username="admin",
            email="admin@example.com",
            password_hash=_hash("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.flush()
        admin_upserted = True

    blog = db.query(Blog).filter_by(slug="chatbot-bilgi-merkezi").first()
    n_blog = 0
    if not blog:
        db.add(
            Blog(
                slug="chatbot-bilgi-merkezi",
                title_tr="Chatbot Bilgi Merkezi",
                title_en="Chatbot Knowledge Center",
                content_tr="Örnek blog içeriği.",
                content_en="Sample blog content.",
                is_published=True,
                published_at=datetime.now(timezone.utc),
                author_id=admin.id,
            )
        )
        n_blog = 1
    else:
        blog.title_tr = "Chatbot Bilgi Merkezi"
        blog.title_en = "Chatbot Knowledge Center"
        blog.content_tr = "Örnek blog içeriği."
        blog.content_en = "Sample blog content."
        blog.author_id = admin.id
        n_blog = 1

    n_qa = 0
    samples = [
        ("health_appointment", "Hastane randevu sistemi arıyoruz", "Sağlık formuna yönlendiriliyorsunuz"),
        ("tourism_hotel", "Otel rezervasyon yazılımı lazım", "Turizm formuna yönlendiriliyorsunuz"),
        ("defense_inquiry", "Askeri lojistik yazılımı hakkında bilgi", "Savunma formuna yönlendiriliyorsunuz"),
        ("education_enrollment", "Öğrenci bilgi sistemi istiyoruz", "Eğitim formuna yönlendiriliyorsunuz"),
    ]
    emb = [0.01 * ((i % 10) + 1) for i in range(EMBEDDING_DIM)]
    for code, q, a in samples:
        intent = intent_map[code]
        exists = (
            db.query(QaEmbedding)
            .filter(QaEmbedding.intent_id == intent.id, QaEmbedding.question == q)
            .first()
        )
        if not exists:
            db.add(
                QaEmbedding(
                    question=q,
                    answer=a,
                    intent_id=intent.id,
                    is_augmented=False,
                    embedding=emb,
                )
            )
            n_qa += 1
        else:
            exists.answer = a

    sess = db.query(ChatSession).filter_by(user_identifier="seed-user").first()
    if not sess:
        sess = ChatSession(session_name="seed-session", user_identifier="seed-user", status="active")
        db.add(sess)
        db.flush()
    sample_session_id = sess.id

    db.commit()

    ids = {
        "sector_health": sector_map["health"].id,
        "sector_tourism": sector_map["tourism"].id,
        "intent_health_appointment": intent_map["health_appointment"].id,
        "admin_id": admin.id,
        "session_id": sample_session_id,
    }
    return SeedResponse(
        sectors_upserted=n_sec,
        intents_upserted=n_int,
        companies_upserted=n_co,
        admin_upserted=admin_upserted,
        blogs_upserted=n_blog,
        qa_upserted=n_qa,
        sample_session_id=sample_session_id,
        ids=ids,
        detail="admin login: admin / admin123",
    )


@router.post("", response_model=SeedResponse)
def seed_demo_data(db: Session = Depends(get_db)):
    """Olması gereken demo veriyi yazar; çöp kayıtları temizler."""
    return _run_seed(db)
