"""Mock veri oluşturur ve günceller — get_or_create mantığıyla çalışır, yıkıcı temizlik yapmaz.
Senkronize edilmiş intents ve qa_embeddings tablosu kısıtlarına uygundur.
"""

from datetime import datetime, timezone
import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models import (
    AdminUser,
    Blog,
    Company,
    Conversation,
    Intent,
    Message,
    QaEmbedding,
    Sector,
    Session as ChatSession,
    AnalyticsEvent,
)

EMBEDDING_DIM = 1024


def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {k: v for k, v in kwargs.items()}
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance, True


def main() -> None:
    db = SessionLocal()

    try:
        # 1. Sektörler
        health, _ = get_or_create(
            db, Sector,
            sector_key="health",
            defaults={"sector_name_tr": "Sağlık", "sector_name_en": "Health"}
        )

        tourism, _ = get_or_create(
            db, Sector,
            sector_key="tourism",
            defaults={"sector_name_tr": "Turizm", "sector_name_en": "Tourism"}
        )

        # 2. Şirketler
        acme, _ = get_or_create(
            db, Company,
            company_name="Acme Sağlık A.Ş.",
            defaults={"sector_id": health.id}
        )

        beta, _ = get_or_create(
            db, Company,
            company_name="Beta Sağlık Teknolojileri",
            defaults={"sector_id": health.id}
        )

        gamma, _ = get_or_create(
            db, Company,
            company_name="Gamma Turizm A.Ş.",
            defaults={"sector_id": tourism.id}
        )

        # 3. Intent kataloğu
        sector_intent, _ = get_or_create(
            db, Intent,
            intent_code="sector_form_request",
            defaults={
                "url": "https://example.com/forms/sector",
                "description": "Kullanıcı bir sektöre özel form talep ediyor",
            }
        )

        general_intent, _ = get_or_create(
            db, Intent,
            intent_code="general_info",
            defaults={
                "url": "https://example.com/forms/general",
                "description": "Kullanıcı genel bilgi istiyor",
            }
        )

        # 4. Oturumlar
        session1, _ = get_or_create(
            db, ChatSession,
            session_name="Web sitesi ziyareti #1",
            user_identifier="anon-user-001",
            defaults={"status": "active"}
        )

        session2, _ = get_or_create(
            db, ChatSession,
            session_name="Web sitesi ziyareti #2",
            user_identifier="anon-user-002",
            defaults={"status": "active"}
        )

        # 5. Konuşmalar
        conv1, _ = get_or_create(
            db, Conversation,
            session_id=session1.id,
        )

        conv2, _ = get_or_create(
            db, Conversation,
            session_id=session2.id,
        )

        # 6. Mesajlar
        get_or_create(
            db, Message,
            conversation_id=conv1.id,
            content="Sağlık teknolojileri hakkında bilgi almak istiyorum",
            role="user",
            defaults={
                "intent": sector_intent.intent_code,
                "source": "web",
                "confidence": 0.9123,
                "response_ms": 100,
            }
        )

        get_or_create(
            db, Message,
            conversation_id=conv1.id,
            content="Sizi sağlık sektöründeki firmalarımıza yönlendiriyorum.",
            role="bot",
            defaults={
                "source": "web",
                "response_ms": 250,
            }
        )

        # 7. Soru-cevap embedding (BGE)
        get_or_create(
            db, QaEmbedding,
            question="Acme Sağlık nedir?",
            intent_id=sector_intent.id,
            defaults={
                "answer": "Acme Sağlık bir sağlık teknolojileri firmasıdır.",
                "is_augmented": False,
                "embedding": [0.015] * EMBEDDING_DIM
            }
        )

        # 8. Analitik Olayları
        get_or_create(
            db, AnalyticsEvent,
            session_id=session1.id,
            intent="sector_form_request",
            defaults={
                "layer_hit": "intent_classifier",
                "response_ms": 35
            }
        )

        # 9. Admin kullanıcı
        hashed_pwd = bcrypt.hashpw(b"test-password-not-for-prod", bcrypt.gensalt()).decode("utf-8")
        admin, _ = get_or_create(
            db, AdminUser,
            username="sinem",
            defaults={
                "email": "sinem@example.com",
                "password_hash": hashed_pwd,
                "role": "admin"
            }
        )

        # 10. Blog kayıtları
        get_or_create(
            db, Blog,
            slug="ilk-yazi",
            defaults={
                "title_tr": "İlk Yazımız",
                "title_en": "Our First Post",
                "content_tr": "Türkçe içerik...",
                "content_en": "English content...",
                "author_id": admin.id,
                "published_at": datetime.now(timezone.utc),
                "is_published": True
            }
        )

        get_or_create(
            db, Blog,
            slug="taslak-yazi",
            defaults={
                "title_tr": "Taslak Yazı",
                "title_en": "Draft Post",
                "content_tr": "Henüz yayınlanmadı...",
                "content_en": "Not published yet...",
                "author_id": admin.id,
                "published_at": None,
                "is_published": False
            }
        )

        db.commit()
        print("Mock veriler güvenli ve mükerrer kayıtsız şekilde tohumlandı/güncellendi.")

    except SQLAlchemyError as error:
        db.rollback()
        print("Veritabanı hatası oluştu. İşlem geri alındı.")
        raise error

    except Exception as error:
        db.rollback()
        print("Beklenmeyen bir hata oluştu. İşlem geri alındı.")
        raise error

    finally:
        db.close()


if __name__ == "__main__":
    main()