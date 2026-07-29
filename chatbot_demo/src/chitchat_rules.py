"""
Katman 1 — Rule-based fast-path (chitchat / gibberish / abuse).

Embedding ve reranker ÇALIŞMAZ; <1ms hedefi.

Karar kuralı (kelime sayısı değil):
  1) Abuse → her zaman OOD
  2) Mesaj yalnızca sosyal yapı taşlarından oluşuyorsa → chitchat (greeting/thanks/identity)
  3) Sosyal + gerçek talep/sektör/soru artığı kaldıysa → None (ML)
  4) Kısa anlamsız → gibberish
  5) Aksi → None (ML)

Örn:
  "Teşekkür ederim, sağ olun" → thanks (saf sosyal yığın)
  "Merhaba, randevu istiyorum" → ML (sosyal + talep artığı)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.chatbot import to_ascii, _normalize

# ---------------------------------------------------------------------------
# Yanıt metinleri (redirect_url her zaman "")
# ---------------------------------------------------------------------------
MSG_GREETING = (
    "Merhaba! Size nasıl yardımcı olabilirim? "
    "Bilişim, Eğitim, Eğlence, Sağlık ve Turizm alanlarında hizmet veriyorum."
)
MSG_IDENTITY = (
    "Ben sizin yönlendirme asistanınızım! İyiyim, teşekkürler. "
    "Size hangi sektörde yardımcı olmamı istersiniz?"
)
MSG_THANKS = (
    "Rica ederim! Başka bir konuda yardıma ihtiyacınız olursa buradayım."
)
MSG_GIBBERISH = (
    "Girdinizi anlayamadım. Lütfen Bilişim, Eğitim, Eğlence, Sağlık veya Turizm "
    "alanıyla ilgili bir soru sorun."
)
MSG_ABUSE = (
    "Lütfen profesyonel ve saygılı bir dil kullanınız. "
    "Size nasıl yardımcı olabilirim?"
)
MSG_OOD_GATE = (
    "Bu konuda size doğrudan yardımcı olamıyorum. "
    "Size Bilişim, Eğitim, Eğlence, Sağlık veya Turizm alanlarında hizmet verebilirim."
)


@dataclass(frozen=True)
class FastPathHit:
    """Katman-1 eşleşmesi."""

    category: str  # greeting | identity | thanks | gibberish | abuse
    sub_intent: str
    status: str  # SUCCESS for social, OOD for gibberish/abuse
    response_message: str
    redirect_url: str = ""
    confidence_score: float = 1.0


# (phrase_tokens, category) — uzun olanlar önce (greedy strip)
_SOCIAL_PHRASES: list[tuple[tuple[str, ...], str]] = [
    (("selamun", "aleykum"), "greeting"),
    (("tesekkur", "ederim"), "thanks"),
    (("iyi", "gunler", "dilerim"), "thanks"),
    (("gorusmek", "uzere"), "thanks"),
    (("hosca", "kalin"), "thanks"),
    (("hosca", "kal"), "thanks"),
    (("bay", "bay"), "thanks"),
    (("ne", "haber"), "identity"),
    (("adin", "ne"), "identity"),
    (("sen", "kimsin"), "identity"),
    (("ne", "yapiyorsun"), "identity"),
    (("bot", "musun"), "identity"),
    (("yapay", "zeka", "misin"), "identity"),
    (("kim", "oldugunu", "soyle"), "identity"),
    (("iyi", "aksamlar"), "greeting"),
    (("iyi", "akasamlar"), "greeting"),
    (("iyi", "geceler"), "greeting"),
    (("iyi", "gunler"), "greeting"),
    (("kolay", "gelsin"), "greeting"),
    (("sag", "olun"), "thanks"),
    (("sag", "ol"), "thanks"),
    (("thank", "you"), "thanks"),
    (("gunaydin",), "greeting"),
    (("merhabalar",), "greeting"),
    (("merhaba",), "greeting"),
    (("selamlar",), "greeting"),
    (("selam",), "greeting"),
    (("mrb",), "greeting"),
    (("slm",), "greeting"),
    (("hey",), "greeting"),
    (("hi",), "greeting"),
    (("hello",), "greeting"),
    (("naber",), "greeting"),
    (("tesekkurler",), "thanks"),
    (("tesekkur",), "thanks"),
    (("eyvallah",), "thanks"),
    (("gorusuruz",), "thanks"),
    (("sagolun",), "thanks"),
    (("sagol",), "thanks"),
    (("thanks",), "thanks"),
    (("ty",), "thanks"),
    (("thx",), "thanks"),
    (("bb",), "thanks"),
    (("baybay",), "thanks"),
    (("nasilsiniz",), "identity"),
    (("nasilsin",), "identity"),
    (("kimsiniz",), "identity"),
    (("kimsin",), "identity"),
]

# Saf sosyal yığında tolere edilen bağlaç / yoğunlaştırıcı (talep değil)
_SOCIAL_FILLERS = frozenset(
    {
        "cok",
        "coklar",
        "gercekten",
        "ben",
        "size",
        "sana",
        "de",
        "da",
        "ve",
        "ile",
        "icin",
        "ya",
        "hocam",
        "abi",
        "abla",
        "beyefendi",
        "hanimefendi",
        "efendim",
        "lutfen",
        "rica",
        "ederim",  # yalnız kalırsa (phrase kaçtıysa) sosyal kalıntı
    }
)

# Bilinen anlamsız dizilimler
_KNOWN_GIBBERISH = frozenset(
    {
        "asdasd",
        "asdf",
        "asdfgh",
        "qwerty",
        "qwe",
        "asd",
        "zzz",
        "xxx",
        "abc",
        "abcd",
        "testtest",
        "aaaa",
        "bbbb",
        "1234",
        "12345",
        "123456",
        "0000",
        "....",
        "????",
        "!!!!",
    }
)

# Hakaret / argo (ASCII-fold; üretim guardrail — genişletilebilir)
_ABUSE_TERMS = frozenset(
    {
        "amk",
        "aq",
        "amq",
        "orospu",
        "siktir",
        "siktirgit",
        "salak",
        "aptal",
        "gerizekali",
        "kahpe",
        "yarrak",
        "serefsiz",
        "ibne",
        "pezevenk",
    }
)

_ONLY_SYMBOLS = re.compile(r"^[\W\d_]+$", re.UNICODE)
_VOWELS = set("aeiouAEIOU")
_SA_GREETING = re.compile(r"^sa+$", re.I)


def _fold(text: str) -> str:
    return to_ascii(_normalize(text or "")).strip()


def _classify_social_token(token: str) -> str | None:
    """Tek token özel kalıplar (sa+, vs.)."""
    if _SA_GREETING.match(token):
        return "greeting"
    return None


def _strip_social(tokens: list[str]) -> tuple[list[str], list[str]]:
    """
    Soldan sağa sosyal phrase'leri soy.
    Döner: (kalan_tokenler, görülen_kategoriler sırayla)
    """
    leftover: list[str] = []
    cats: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        matched = False
        for phrase, cat in _SOCIAL_PHRASES:
            plen = len(phrase)
            if i + plen <= n and tuple(tokens[i : i + plen]) == phrase:
                cats.append(cat)
                i += plen
                matched = True
                break
        if matched:
            continue
        special = _classify_social_token(tokens[i])
        if special:
            cats.append(special)
            i += 1
            continue
        leftover.append(tokens[i])
        i += 1
    return leftover, cats


def _pick_social_category(cats: list[str]) -> str:
    """Yığın içinde öncelik: thanks > identity > greeting (son görülen soft)."""
    if "thanks" in cats:
        return "thanks"
    if "identity" in cats:
        return "identity"
    return "greeting"


def _is_pure_social(tokens: list[str]) -> tuple[bool, str | None]:
    """Yalnızca sosyal yapı taşları (+ filler) ise (True, category)."""
    if not tokens:
        return False, None
    leftover, cats = _strip_social(tokens)
    meaningful = [t for t in leftover if t not in _SOCIAL_FILLERS]
    if meaningful:
        return False, None
    if not cats:
        return False, None
    return True, _pick_social_category(cats)


def _is_gibberish(folded: str) -> bool:
    if not folded:
        return True
    compact = re.sub(r"\s+", "", folded)
    if len(compact) < 2:
        return True
    if compact in _KNOWN_GIBBERISH:
        return True
    if _ONLY_SYMBOLS.match(compact):
        return True
    if len(set(compact)) <= 2 and len(compact) >= 4:
        return True
    letters = [c for c in compact if c.isalpha()]
    if len(letters) >= 5 and not any(c in _VOWELS for c in letters):
        return True
    return False


def _has_abuse(folded: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", folded.lower())
    for t in tokens:
        if t in _ABUSE_TERMS:
            return True
        for term in _ABUSE_TERMS:
            if len(term) >= 5 and len(t) > len(term) and t.startswith(term):
                return True
    return False


def match_fast_path(query: str) -> FastPathHit | None:
    """
    Katman 1. Eşleşme yoksa None → ML katmanına geç.
    Saf sosyal yığın → chitchat; sosyal + talep artığı → None.
    """
    raw = (query or "").strip()
    folded = _fold(raw)
    if not folded:
        return FastPathHit(
            category="gibberish",
            sub_intent="ood.gibberish",
            status="OOD",
            response_message=MSG_GIBBERISH,
            confidence_score=1.0,
        )

    # 1) Abuse — içerik olsa bile guardrail
    if _has_abuse(folded):
        return FastPathHit(
            category="abuse",
            sub_intent="ood.abuse",
            status="OOD",
            response_message=MSG_ABUSE,
            confidence_score=1.0,
        )

    tokens = re.findall(r"[a-z0-9]+", folded.lower())

    # 2) Saf sosyal (tek veya yığılmış: "teşekkür ederim, sağ olun")
    pure, cat = _is_pure_social(tokens)
    if pure and cat == "greeting":
        return FastPathHit(
            category="greeting",
            sub_intent="chitchat.greeting",
            status="SUCCESS",
            response_message=MSG_GREETING,
            confidence_score=1.0,
        )
    if pure and cat == "thanks":
        return FastPathHit(
            category="thanks",
            sub_intent="chitchat.thanks",
            status="SUCCESS",
            response_message=MSG_THANKS,
            confidence_score=1.0,
        )
    if pure and cat == "identity":
        return FastPathHit(
            category="identity",
            sub_intent="chitchat.identity",
            status="SUCCESS",
            response_message=MSG_IDENTITY,
            confidence_score=1.0,
        )

    # 3) Gibberish (yalnızca kısa / anlamsız — uzun sektörel metni ezme)
    if len(folded) <= 48 and _is_gibberish(folded):
        return FastPathHit(
            category="gibberish",
            sub_intent="ood.gibberish",
            status="OOD",
            response_message=MSG_GIBBERISH,
            confidence_score=1.0,
        )

    # 4) Gerçek talep / sektör / soru → ML
    return None
