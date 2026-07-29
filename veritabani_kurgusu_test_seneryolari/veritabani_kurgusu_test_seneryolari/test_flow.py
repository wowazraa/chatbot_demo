"""SQLAlchemy modelleri üzerinden uçtan uca akış testi (schema v6 - Sadeleştirilmiş).

Varsayılan: assert'ler çalışır, transaction rollback edilir (DB kirlenmez).
Kalıcı seed için: SEED_COMMIT=1
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

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

SEED_COMMIT = os.environ.get("SEED_COMMIT", "").strip() in {"1", "true", "True", "yes"}


def main() -> None:
    db = SessionLocal()
    try:
        # Benzersizlik sağlamak için uuid bazlı suffix üretiyoruz
        suffix = uuid.uuid4().hex[:8]
        
        # 1. Sektör oluşturma
        sector_key = f"health_{suffix}"
        sector = Sector(sector_key=sector_key, sector_name_tr="sağlık", sector_name_en="health")
        db.add(sector)
        db.flush()

        # 2. Firma oluşturma
        company_name_acme = f"Acme Sağlık A.Ş. {suffix}"
        acme = Company(company_name=company_name_acme, sector_id=sector.id)
        db.add(acme)
        db.flush()

        # 3. Intent oluşturma
        intent_code = f"sector_form_request_{suffix}"
        intent = Intent(
            intent_code=intent_code,
            url="https://example.com/forms/saglik",
            description="Kullanıcı bir sektöre özel form talep ediyor",
        )
        db.add(intent)
        db.flush()

        # 4. Oturum oluşturma
        chat_session = ChatSession(
            session_name=f"Test Oturumu {suffix}",
            user_identifier=f"user-{suffix}",
        )
        db.add(chat_session)
        db.flush()

        # 5. Konuşma oluşturma
        conv = Conversation(session_id=chat_session.id)
        db.add(conv)
        db.flush()

        # 6. Mesaj oluşturma
        msg_user = Message(
            conversation_id=conv.id,
            content="Merhaba, sağlık hizmetleri hakkında bilgi alabilir miyim?",
            role="user",
            intent=intent.intent_code,
            source="web",
            confidence=0.9200,
        )
        msg_bot = Message(
            conversation_id=conv.id,
            content="Tabii ki, size sağlık konusunda yardımcı olabilirim.",
            role="bot",
            source="web",
        )
        db.add_all([msg_user, msg_bot])
        db.flush()

        # 7. Soru-cevap embedding
        qa_embedding = QaEmbedding(
            question="Acme Sağlık firması nedir?",
            answer="Acme Sağlık firması bir sağlık kuruluşudur.",
            intent_id=intent.id,
            is_augmented=False,
            embedding=[0.01] * 1024,
        )
        db.add(qa_embedding)
        db.flush()

        # 8. Analitik olayı oluşturma
        analytics_event = AnalyticsEvent(
            session_id=chat_session.id,
            intent=intent.intent_code,
            layer_hit="direct_match",
            response_ms=150,
        )
        db.add(analytics_event)
        db.flush()

        # 9. Admin kullanıcı oluşturma
        admin = AdminUser(
            username=f"sinem_{suffix}",
            email=f"sinem_{suffix}@example.com",
            password_hash=bcrypt.hashpw(
                b"test-password-not-for-prod",
                bcrypt.gensalt(),
            ).decode("utf-8"),
            role="admin",
        )
        db.add(admin)
        db.flush()

        # 10. Blog oluşturma
        blog = Blog(
            slug=f"ilk-yazi-{suffix}",
            title_tr="İlk Yazımız",
            title_en="Our First Post",
            content_tr="Türkçe içerik...",
            content_en="English content...",
            author_id=admin.id,
            published_at=datetime.now(timezone.utc),
            is_published=True,
        )
        db.add(blog)
        db.flush()

        # Yayın tarihi olmadan yayınlama kontrolü (Event Listener doğrulama testi)
        blog_validation_savepoint = db.begin_nested()
        try:
            invalid_blog = Blog(
                slug=f"bad-publish-{suffix}",
                title_tr="Geçersiz",
                title_en="Invalid",
                content_tr="x",
                content_en="x",
                is_published=True,
                published_at=None,
            )
            db.add(invalid_blog)
            db.flush()
            raise AssertionError("published_at olmadan blog yayınlanamamalıydı.")
        except (DBAPIError, ValueError):
            blog_validation_savepoint.rollback()

        # 11. Unique constraint testi
        unique_savepoint = db.begin_nested()
        try:
            duplicate_sector = Sector(
                sector_key=sector_key,
                sector_name_tr="kopya",
                sector_name_en="copy",
            )
            db.add(duplicate_sector)
            db.flush()
            raise AssertionError("Mükerrer sector_key başarısız olmalıydı.")
        except (DBAPIError, ValueError):
            unique_savepoint.rollback()

        # Transcript View kontrolü
        view_result = db.execute(
            text("SELECT transcript FROM session_transcripts WHERE session_id = :session_id"),
            {"session_id": chat_session.id}
        ).scalar()
        assert view_result is not None
        assert "user: Merhaba" in view_result

        print("OK: Transcript view içeriği ->", repr(view_result))
        print("OK: Blog ->", blog.slug, "published=", blog.is_published)

        if SEED_COMMIT:
            db.commit()
            print("SEED_COMMIT=1 — değişiklikler commit edildi.")
        else:
            db.rollback()
            print("Rollback — veritabanında kalıcı test verisi bırakılmadı.")

        print("Tüm ORM testleri başarıyla tamamlandı.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()