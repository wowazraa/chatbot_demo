"""Anahtar kelime / regex intent eşleşmesi (K1 + chitchat fast-path)."""

from __future__ import annotations

from app.core.chitchat_rules import match_fast_path
from app.core.k1_guardrails import (
    DECISION_THRESHOLD,
    check_ood_reject,
    check_restricted_domain,
    extract_active_clause,
    match_any_sector,
)


class KeywordService:
    """Katman 1 / 1.5 / 1.6 — kural tabanlı intent eşleşmesi."""

    DECISION_THRESHOLD = DECISION_THRESHOLD

    def match_fast_path(self, query: str):
        return match_fast_path(query)

    def match_sector(self, query: str) -> str | None:
        return match_any_sector(query)

    def check_ood(self, query: str) -> bool:
        return check_ood_reject(query)

    def check_restricted(self, query: str) -> bool:
        return check_restricted_domain(query)

    def extract_clause(self, query: str) -> str:
        return extract_active_clause(query)


__all__ = [
    "DECISION_THRESHOLD",
    "KeywordService",
    "match_any_sector",
    "match_fast_path",
    "check_ood_reject",
]
