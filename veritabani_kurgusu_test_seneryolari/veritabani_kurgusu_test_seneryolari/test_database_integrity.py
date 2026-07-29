"""PostgreSQL veri bütünlüğü ve cascade davranışı testleri.

Bu dosya mevcut proje dosyalarını değiştirmez ve test verilerini kalıcı
olarak kaydetmez. Her test ayrı bir transaction içinde çalışır ve test
sonunda rollback edilir.

Çalıştırma:
    python -m unittest -v test_database_integrity.py
"""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from database import engine
from models import (
    AdminUser,
    AnalyticsEvent,
    Blog,
    Conversation,
    Intent,
    Message,
    QaEmbedding,
    Sector,
    Session as ChatSession,
)

EMBEDDING_DIMENSION = 1024


class DatabaseIntegrityTests(unittest.TestCase):
    """Veritabanı kısıtlarını gerçek PostgreSQL üzerinde doğrular."""

    def setUp(self) -> None:
        self.connection = engine.connect()
        self.transaction = self.connection.begin()

        self.db = OrmSession(
            bind=self.connection,
            autoflush=False,
            expire_on_commit=False,
        )

        self.suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        self.db.close()

        if self.transaction.is_active:
            self.transaction.rollback()

        self.connection.close()

    def _create_session(self) -> ChatSession:
        chat_session = ChatSession(
            session_name=f"Integrity Test {self.suffix}",
            user_identifier=f"test-user-{self.suffix}",
        )

        self.db.add(chat_session)
        self.db.flush()

        return chat_session

    def _create_conversation(
        self,
        session_id: int,
    ) -> Conversation:
        conversation = Conversation(
            session_id=session_id,
        )

        self.db.add(conversation)
        self.db.flush()

        return conversation

    def test_deleting_session_cascades_to_conversations_and_analytics(
        self,
    ) -> None:
        chat_session = self._create_session()
        conversation = self._create_conversation(chat_session.id)

        analytics_event = AnalyticsEvent(
            session_id=chat_session.id,
            intent="integrity_test",
            layer_hit="database",
            response_ms=25,
        )

        self.db.add(analytics_event)
        self.db.flush()

        session_id = chat_session.id
        conversation_id = conversation.id
        analytics_event_id = analytics_event.id

        self.db.execute(
            text(
                """
                DELETE FROM sessions
                WHERE id = :session_id
                """
            ),
            {
                "session_id": session_id,
            },
        )
        self.db.flush()

        conversation_count = self.db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.id == conversation_id)
        )

        analytics_count = self.db.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.id == analytics_event_id)
        )

        self.assertEqual(conversation_count, 0)
        self.assertEqual(analytics_count, 0)

    def test_deleting_conversation_cascades_to_messages(
        self,
    ) -> None:
        chat_session = self._create_session()
        conversation = self._create_conversation(chat_session.id)

        message = Message(
            conversation_id=conversation.id,
            content="Cascade testi",
            role="user",
            source="test",
        )

        self.db.add(message)
        self.db.flush()

        conversation_id = conversation.id
        message_id = message.id

        self.db.execute(
            text(
                """
                DELETE FROM conversations
                WHERE id = :conversation_id
                """
            ),
            {
                "conversation_id": conversation_id,
            },
        )
        self.db.flush()

        message_count = self.db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.id == message_id)
        )

        self.assertEqual(message_count, 0)

    def test_messages_reject_invalid_role(self) -> None:
        chat_session = self._create_session()
        conversation = self._create_conversation(chat_session.id)

        savepoint = self.db.begin_nested()

        try:
            invalid_message = Message(
                conversation_id=conversation.id,
                content="Geçersiz rol testi",
                role="admin",
                source="test",
            )

            self.db.add(invalid_message)

            with self.assertRaises(IntegrityError):
                self.db.flush()

        finally:
            savepoint.rollback()

    def test_qa_embeddings_reject_empty_question_or_answer(self) -> None:
        """Boş veya boşluk karakterlerinden oluşan soru/cevap girişlerinin reddedildiğini doğrular."""
        intent = Intent(
            intent_code=f"intent-test-empty-qa-{self.suffix}",
            url=f"https://example.com/intents/{self.suffix}",
        )
        self.db.add(intent)
        self.db.flush()

        # Boş soru testi
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                qa_embedding = QaEmbedding(
                    question="",
                    answer="Geçerli cevap",
                    intent_id=intent.id,
                    embedding=[0.01] * EMBEDDING_DIMENSION,
                )
                self.db.add(qa_embedding)
                self.db.flush()
        finally:
            savepoint.rollback()

        # Boşluklu soru testi
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                qa_embedding = QaEmbedding(
                    question="   ",
                    answer="Geçerli cevap",
                    intent_id=intent.id,
                    embedding=[0.01] * EMBEDDING_DIMENSION,
                )
                self.db.add(qa_embedding)
                self.db.flush()
        finally:
            savepoint.rollback()

        # Boş cevap testi
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                qa_embedding = QaEmbedding(
                    question="Geçerli soru",
                    answer="",
                    intent_id=intent.id,
                    embedding=[0.01] * EMBEDDING_DIMENSION,
                )
                self.db.add(qa_embedding)
                self.db.flush()
        finally:
            savepoint.rollback()

        # Boşluklu cevap testi
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                qa_embedding = QaEmbedding(
                    question="Geçerli soru",
                    answer="   ",
                    intent_id=intent.id,
                    embedding=[0.01] * EMBEDDING_DIMENSION,
                )
                self.db.add(qa_embedding)
                self.db.flush()
        finally:
            savepoint.rollback()

    def test_empty_intent_url_is_rejected(self) -> None:
        """Boş veya boşluk karakterlerinden oluşan intent URL'lerinin reddedildiğini doğrular."""
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                intent = Intent(
                    intent_code=f"intent-test-empty-url-{self.suffix}",
                    url="",
                )
                self.db.add(intent)
                self.db.flush()
        finally:
            savepoint.rollback()

        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                intent = Intent(
                    intent_code=f"intent-test-blank-url-{self.suffix}",
                    url="   ",
                )
                self.db.add(intent)
                self.db.flush()
        finally:
            savepoint.rollback()

    def test_empty_intent_code_is_rejected(self) -> None:
        """Boş veya boşluk karakterlerinden oluşan intent_code değerlerinin reddedildiğini doğrular."""
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                intent = Intent(
                    intent_code="",
                    url=f"https://example.com/intents/{self.suffix}",
                )
                self.db.add(intent)
                self.db.flush()
        finally:
            savepoint.rollback()

        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                intent = Intent(
                    intent_code="   ",
                    url=f"https://example.com/intents/{self.suffix}",
                )
                self.db.add(intent)
                self.db.flush()
        finally:
            savepoint.rollback()

    def test_qa_embeddings_reject_invalid_intent_id(self) -> None:
        """Var olmayan intent_id ile qa_embeddings kaydı eklenmesinin reddedildiğini (FK ihlali) doğrular."""
        savepoint = self.db.begin_nested()
        try:
            with self.assertRaises(IntegrityError):
                qa_embedding = QaEmbedding(
                    question="Soru",
                    answer="Cevap",
                    intent_id=-9999,
                    embedding=[0.01] * EMBEDDING_DIMENSION,
                )
                self.db.add(qa_embedding)
                self.db.flush()
        finally:
            savepoint.rollback()

    def test_qa_embeddings_save_smoothly_with_valid_intent(self) -> None:
        """Geçerli bir intent ile qa_embeddings kaydının pürüzsüz eklendiğini doğrular."""
        intent = Intent(
            intent_code=f"intent-test-smooth-{self.suffix}",
            url=f"https://example.com/intents/{self.suffix}",
        )
        self.db.add(intent)
        self.db.flush()

        qa_embedding = QaEmbedding(
            question="Soru",
            answer="Cevap",
            intent_id=intent.id,
            embedding=[0.01] * EMBEDDING_DIMENSION,
        )
        self.db.add(qa_embedding)
        self.db.flush()

        self.assertIsNotNone(qa_embedding.id)

    def test_intent_delete_restricted_by_qa_embeddings(self) -> None:
        """Bağlı qa_embeddings varken parent intent silinmeye çalışıldığında RESTRICT nedeniyle engellendiğini doğrular."""
        intent = Intent(
            intent_code=f"intent-test-restrict-{self.suffix}",
            url=f"https://example.com/intents/{self.suffix}",
        )
        self.db.add(intent)
        self.db.flush()

        qa_embedding = QaEmbedding(
            question="Soru",
            answer="Cevap",
            intent_id=intent.id,
            embedding=[0.01] * EMBEDDING_DIMENSION,
        )
        self.db.add(qa_embedding)
        self.db.flush()

        savepoint = self.db.begin_nested()
        try:
            self.db.delete(intent)
            with self.assertRaises(IntegrityError):
                self.db.flush()
        finally:
            savepoint.rollback()

    def test_duplicate_sector_key_is_rejected(self) -> None:
        sector_key = f"sector-{self.suffix}"

        first_sector = Sector(
            sector_key=sector_key,
            sector_name_tr="Test Sektörü",
            sector_name_en="Test Sector",
        )

        self.db.add(first_sector)
        self.db.flush()

        savepoint = self.db.begin_nested()

        try:
            duplicate_sector = Sector(
                sector_key=sector_key,
                sector_name_tr="Tekrar",
                sector_name_en="Duplicate",
            )

            self.db.add(duplicate_sector)

            with self.assertRaises(IntegrityError):
                self.db.flush()

        finally:
            savepoint.rollback()

    def test_duplicate_intent_code_is_rejected(self) -> None:
        intent_code = f"intent-{self.suffix}"

        first_intent = Intent(
            intent_code=intent_code,
            url=f"https://example.com/intents/{self.suffix}/first",
            description="İlk kayıt",
        )

        self.db.add(first_intent)
        self.db.flush()

        savepoint = self.db.begin_nested()

        try:
            duplicate_intent = Intent(
                intent_code=intent_code,
                url=(
                    f"https://example.com/intents/"
                    f"{self.suffix}/duplicate"
                ),
                description="Mükerrer kayıt",
            )

            self.db.add(duplicate_intent)

            with self.assertRaises(IntegrityError):
                self.db.flush()

        finally:
            savepoint.rollback()

    def test_published_blog_requires_published_at(self) -> None:
        admin = AdminUser(
            username=f"admin-{self.suffix}",
            email=f"admin-{self.suffix}@example.com",
            password_hash="test-only-password-hash",
            role="admin",
        )

        self.db.add(admin)
        self.db.flush()

        savepoint = self.db.begin_nested()

        try:
            invalid_blog = Blog(
                slug=f"invalid-blog-{self.suffix}",
                title_tr="Geçersiz Blog",
                title_en="Invalid Blog",
                content_tr="İçerik",
                content_en="Content",
                author_id=admin.id,
                is_published=True,
                published_at=None,
            )

            self.db.add(invalid_blog)

            with self.assertRaises(ValueError):
                self.db.flush()

        finally:
            savepoint.rollback()

    def test_valid_published_blog_is_accepted(self) -> None:
        admin = AdminUser(
            username=f"publisher-{self.suffix}",
            email=f"publisher-{self.suffix}@example.com",
            password_hash="test-only-password-hash",
            role="editor",
        )

        self.db.add(admin)
        self.db.flush()

        blog = Blog(
            slug=f"valid-blog-{self.suffix}",
            title_tr="Geçerli Blog",
            title_en="Valid Blog",
            content_tr="İçerik",
            content_en="Content",
            author_id=admin.id,
            is_published=True,
            published_at=datetime.now(timezone.utc),
        )

        self.db.add(blog)
        self.db.flush()

        self.assertIsNotNone(blog.id)
        self.assertTrue(blog.is_published)
        self.assertIsNotNone(blog.published_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)