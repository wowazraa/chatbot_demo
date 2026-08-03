"""Fallback — belirsiz/OOD yanıtları ve aktif öğrenme kaydı."""

from __future__ import annotations

from app.core.intent_contract import resolve_redirect_url, resolve_response_message
from app.services.unresolved_logger import log_unresolved_query as log_unresolved


class FallbackService:
    """Düşük güven / OOD durumlarında yanıt üretimi ve kayıt."""

    def resolve_response(
        self,
        sector: str,
        sub_intent: str,
        status: str,
        *,
        redirect_url: str = "",
        lang: str = "tr",
    ) -> str:
        return resolve_response_message(
            sector, sub_intent, status, redirect_url=redirect_url, lang=lang
        )

    def resolve_url(self, sector: str, sub_intent: str, status: str) -> str:
        return resolve_redirect_url(sector, sub_intent, status)

    def log_unresolved(self, query: str, **kwargs) -> None:
        log_unresolved(query, **kwargs)


_SECTOR_TR: dict[str, str] = {
    "saglik": "sağlık",
    "turizm": "turizm",
    "eglence": "eğlence",
    "egitim": "eğitim",
    "bilisim": "bilişim",
}


def build_chat_reply(st: str, sector: str, url: str | None) -> str:
    """HTTP katmanı için kullanıcıya gösterilecek metin."""
    if st == "SUCCESS" and url:
        tr = _SECTOR_TR.get(sector, sector)
        return (
            f"Talebinizi {tr} sektörüyle ilişkilendirdim. "
            f"İlgili forma buradan ulaşabilirsiniz: {url}"
        )
    if st == "SUCCESS":
        tr = _SECTOR_TR.get(sector, sector)
        return f"Talebinizi {tr} sektörüyle ilişkilendirdim."
    if st == "UNCERTAIN":
        return (
            "Talebinizi net anlayamadım. Hangi sektör / süreç için "
            "destek aradığınızı kısaca yazar mısınız?"
        )
    return (
        "Bu konu şu anki B2B hizmet kapsamımız dışındadır. "
        "Bilişim, eğitim, eğlence, sağlık veya turizm alanlarındaki talepleriniz için yardımcı olabilirim."
    )


__all__ = ["FallbackService", "build_chat_reply"]
