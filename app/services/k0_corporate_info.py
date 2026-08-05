"""K0 — kurumsal bilgi fast-path (tanım kalıbı + terim sözlüğü)."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_allintos_site_url
from app.core.record_types import KAYIT_TIPI_KURUMSAL
from app.services.fallback_service import normalize_reply_lang

ROOT = Path(__file__).resolve().parents[2]
PREPARED_PATH = ROOT / "data" / "external" / "kurumsal_326_prepared.json"

_DEFINITION_TR = re.compile(
    r"\b(nedir|ne demek|ne anlama|kısaca|kisaca|açıkla|acikla|anlat|tanım|tanim)\b",
    re.IGNORECASE,
)
_DEFINITION_EN = re.compile(
    r"\b(what is|what's|who is|explain|tell me about|meaning of|can you explain)\b",
    re.IGNORECASE,
)

# canonical_key → surface aliases (lowercase)
CORPORATE_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "ddx": ("ddx", "ddx+", "ddx plus", "dijital dönüşüm indeksi", "digital transformation index"),
    "tubitak": ("tübitak", "tubitak", "tübitak'ın", "tubitak'in"),
    "tusside": ("tüsside", "tusside", "tüsside'nin", "tusside'nin"),
    "allintos": ("allintos", "alintos", "alientos"),
    "buyumevizyon": ("buyumevizyon", "büyümevizyon", "buyume vizyon"),
    "trl": ("trl", "technology readiness level", "teknoloji hazırlık seviyesi", "teknoloji hazirlik"),
    "turquality": ("turquality", "tur quality"),
    "e_turquality": ("e-turquality", "e turquality", "eturquality"),
    "dijital_olgunluk": ("dijital olgunluk", "dijital olgunluk testi", "digital maturity"),
    "kosgeb": ("kosgeb", "kosgeb dijital dönüşüm", "kosgeb dijital donusum"),
    "tesvik": ("teşvik", "tesvik", "teşvik türleri", "tesvik turleri", "yatırım teşvik", "yatirim tesvik"),
    "globallesme": ("globalleşme", "globallesme", "globalization"),
    "ai_danisman": ("ai danışman", "ai danisman", "ai danışmanlık", "ai consultant"),
    "kvkk": ("kvkk", "kişisel veriler", "kisiel veriler"),
    "dijital_donusum": ("dijital dönüşüm", "dijital donusum", "digital transformation"),
    "metodoloji": ("allintos metodolojisi", "metodoloji"),
    "hbys": ("hbys",),
    "lms": ("lms",),
    "crm": ("crm",),
    "erp": ("erp",),
    "api": ("api",),
    "devops": ("devops",),
    "bulut": ("bulut bilişim", "cloud computing"),
}

# Tanım kalıbı olmadan K0 — yalnızca net kurumsal terimler (B2B jargon değil)
TERM_ONLY_KEYS = frozenset({
    "ddx",
    "tubitak",
    "tusside",
    "allintos",
    "buyumevizyon",
    "trl",
    "turquality",
    "e_turquality",
    "dijital_olgunluk",
    "kosgeb",
    "tesvik",
    "globallesme",
    "ai_danisman",
    "kvkk",
    "dijital_donusum",
    "metodoloji",
})

_SERVICE_INTENT = re.compile(
    r"\b("
    r"istiyoruz|istiyorum|istiyor|ihtiyacımız|ihtiyacimiz|ihtiyacım|ihtiyacim|"
    r"almak istiyoruz|almak istiyorum|başlatmak istiyoruz|baslatmak istiyoruz|"
    r"danışmanlık istiyoruz|danismanlik istiyoruz|danışmanlık almak|danismanlik almak|"
    r"danışmanlık|danismanlik|hizmeti almak|hizmet almak|hizmet istiyoruz|"
    r"lazım|lazim|arıyoruz|ariyoruz|arayış|platform|sistem|"
    r"yazılım|yazilim|entegrasyon|randevu|rezervasyon|hastane|hastanel|otel|oteller|"
    r"okul|üniversite|universite|kurulum|demo|teklif|fiyat|başvurusu|basvurusu|"
    r"need|looking for|software|integration|hospital|hotel|we want|we need"
    r")\b",
    re.IGNORECASE,
)

_EN_DEF = re.compile(r"\b(what is|what's|how do|explain|tell me about)\b", re.IGNORECASE)

# Kurumsal cevap metninin sonundaki gömülü path/URL kuyrukları (dataset'ten gelir)
_CEVAP_URL_TAIL = re.compile(
    r"\s*(?:"
    r"Detayl[ıi]\s+bilgi|Daha\s+fazla\s+bilgi|"
    r"Detailed\s+(?:info|information)|More\s+(?:info|information)"
    r")\s*:\s*(?:https?://\S+|/\S+)\s*$",
    re.IGNORECASE,
)


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def _load_records() -> list[dict[str, Any]]:
    if not PREPARED_PATH.exists():
        return []
    data = json.loads(PREPARED_PATH.read_text(encoding="utf-8"))
    return list(data.get("kayitlar") or [])


def _resolve_kaynak_url(raw: str | None) -> str:
    u = (raw or "").strip()
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    base = get_allintos_site_url()
    return f"{base}{u}" if u.startswith("/") else f"{base}/{u.lstrip('/')}"


def sanitize_corporate_cevap(text: str) -> str:
    """Kurumsal/BILGI cevabından gömülü kaynak URL kuyruğunu temizle."""
    t = (text or "").strip()
    prev = None
    while t and t != prev:
        prev = t
        t = _CEVAP_URL_TAIL.sub("", t).strip()
    return t


def _has_definition_pattern(q: str) -> bool:
    return bool(_DEFINITION_TR.search(q) or _DEFINITION_EN.search(q))


def _detect_term_key(q_folded: str) -> str | None:
    q = (q_folded or "").strip()
    if not q:
        return None

    tokens = q.split()
    # Tek kelime: birebir alias eşleşmesi (substring false-positive önleme)
    if len(tokens) == 1:
        t = tokens[0]
        for key, aliases in CORPORATE_TERM_ALIASES.items():
            for alias in aliases:
                if _fold(alias) == t:
                    return key

    best_key: str | None = None
    best_len = 0
    for key, aliases in CORPORATE_TERM_ALIASES.items():
        for alias in aliases:
            af = _fold(alias)
            if af and af in q and len(af) > best_len:
                best_key = key
                best_len = len(af)
    return best_key


def _konu_term_score(term_key: str, rec: dict[str, Any]) -> int:
    konu = _fold(rec.get("konu_etiketi") or "")
    tk = term_key.replace("_", "")
    kn = konu.replace("_", "")

    # E-Turquality vs Turquality ayrımı (kurumsal_e_turquality ≠ kurumsal_e_e_turquality)
    if term_key == "e_turquality":
        if "e_e_turquality" in konu:
            return 100
        if konu == "kurumsal_e_turquality":
            return 20
    if term_key == "turquality":
        if "e_e_turquality" in konu:
            return 15
        if konu == "kurumsal_e_turquality":
            return 100

    if konu in (f"kurumsal_c_{term_key}", f"kurumsal_{term_key}"):
        return 100
    if konu.endswith(f"_{term_key}") or kn.endswith(tk):
        return 95
    if f"_{term_key}_genel" in konu or konu.endswith(f"_{term_key}_genel"):
        return 90
    if f"_{term_key}_form" in konu:
        return 35
    if tk in kn:
        return 50
    return 0


def _record_lang(rec: dict[str, Any]) -> str:
    """Kayıt dili — dataset lang alanı veya mesaj/cevap heuristiği."""
    raw = (rec.get("lang") or "").strip().lower()
    if raw.startswith("en"):
        return "en"
    if raw.startswith("tr"):
        return "tr"
    msg = _fold(rec.get("mesaj") or "")
    cevap = rec.get("cevap") or ""
    if _EN_DEF.search(msg) or cevap.lstrip().startswith(
        ("DDX is", "Turquality is", "E-Turquality is", "Allintos is", "TRL is", "The ")
    ):
        return "en"
    return "tr"


def _reply_lang_score(rec: dict[str, Any], reply_lang: str) -> int:
    """Sayfa/istek dili ile kayıt dili eşleşmesi — birincil tie-breaker."""
    target = normalize_reply_lang(reply_lang)
    return 100 if _record_lang(rec) == target else -100


def _msg_term_score(term_key: str, query_folded: str, rec: dict[str, Any]) -> int:
    msg = _fold(rec.get("mesaj") or "")
    if not msg:
        return 0
    if msg == query_folded:
        return 100
    aliases = [_fold(a) for a in CORPORATE_TERM_ALIASES.get(term_key, ())]
    if query_folded in aliases and msg in aliases:
        return 95
    for af in sorted(aliases, key=len, reverse=True):
        if msg == af:
            return 90
        if msg.startswith(af + " ") or (len(af) >= 4 and msg.startswith(af)):
            return 70
        if len(af) >= 3 and af in msg:
            return 40 + min(len(af), 15)
    return 0


def _pick_record(term_key: str, query_folded: str, reply_lang: str = "tr") -> dict[str, Any] | None:
    records = _load_records()
    if not records:
        return None

    exact: list[dict[str, Any]] = []
    for rec in records:
        msg = _fold(rec.get("normalize_mesaj") or rec.get("mesaj") or "")
        if msg and msg == query_folded:
            exact.append(rec)
    if exact:
        target = normalize_reply_lang(reply_lang)
        for rec in exact:
            if _record_lang(rec) == target:
                return rec
        return exact[0]

    best_rec: dict[str, Any] | None = None
    best_score = (-999, -999, -999)
    for rec in records:
        ks = _konu_term_score(term_key, rec)
        ms = _msg_term_score(term_key, query_folded, rec)
        ls = _reply_lang_score(rec, reply_lang)
        if ks == 0 and ms == 0:
            continue
        score = (ks, ls, ms)
        if score > best_score:
            best_score = score
            best_rec = rec
    return best_rec


def pick_kurumsal_hit_for_lang(hits: list[Any], reply_lang: str) -> Any | None:
    """K2 kurumsal fallback — sayfa diline uygun adayı seç."""
    if not hits:
        return None
    target = normalize_reply_lang(reply_lang)
    for h in hits:
        meta = getattr(h, "record_meta", None) or {}
        lang = (meta.get("lang") or "tr").strip().lower()
        if lang.startswith(target):
            return h
    return hits[0]


def _has_strong_service_signal(query: str) -> bool:
    """Güçlü hizmet/sektör niyeti — term-only K0'ı engeller."""
    from app.core.k1_guardrails import match_any_sector

    if match_any_sector(query):
        return True
    return bool(_SERVICE_INTENT.search(query or ""))


def _match_corporate_term(query: str, reply_lang: str = "tr") -> dict[str, Any] | None:
    """Ortak eşleştirme — tanım veya term-only yol."""
    q_raw = (query or "").strip()
    if not q_raw:
        return None

    q_folded = _fold(q_raw)
    term_key = _detect_term_key(q_folded)
    if not term_key:
        return None

    # Güçlü hizmet niyeti — tanım kalıbı olsa bile K0'ı atla (K1/K2 sektör akışı)
    if _has_strong_service_signal(q_raw):
        return None

    has_def = _has_definition_pattern(q_raw)
    if not has_def:
        if term_key not in TERM_ONLY_KEYS:
            return None

    rec = _pick_record(term_key, q_folded, reply_lang=reply_lang)
    if not rec:
        return None

    cevap = sanitize_corporate_cevap((rec.get("cevap") or "").strip())
    if not cevap:
        return None

    return {
        "kayit_tipi": KAYIT_TIPI_KURUMSAL,
        "cevap": cevap,
        "kaynak_url": "",
        "konu_etiketi": rec.get("konu_etiketi") or "",
        "source_id": str(rec.get("id") or ""),
        "matched_term": term_key,
        "layer": "k0",
        "k0_mode": "definition" if has_def else "term_only",
    }


def try_k0_corporate_info(query: str, reply_lang: str | None = None) -> dict[str, Any] | None:
    """
    Tanım kalıbı + bilinen terim → {cevap, kaynak_url, ...}.
    reply_lang: widget/API sayfa dili (tr|en) — cevap dili buna göre seçilir.
    """
    return _match_corporate_term(query, reply_lang=normalize_reply_lang(reply_lang))


__all__ = [
    "CORPORATE_TERM_ALIASES",
    "try_k0_corporate_info",
    "sanitize_corporate_cevap",
    "pick_kurumsal_hit_for_lang",
    "_resolve_kaynak_url",
]
