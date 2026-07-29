"""
chatbot_flow.py
================
Intent tespiti + konuşma döngüsü.

Büyük Filo canlı testinden uyarlanan korumalar:
  1) Session state — normal / clarification / lead_capture
  2) Çıkış komutları her state'te önce kontrol edilir (kilitlenmeyi önler)
  3) Slot (isim/iletişim) doğrulama — körü körüne kabul yok
  4) Form URL sonrası state normal'e döner; kullanıcı yeni soru sorabilir
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from intent_tespiti_prototip import (
    MODEL_ADI,
    SIMILARITY_ESIK,
    SEKTOR_REFERANSLARI,
    intent_tespit_et,
)

# ---------------------------------------------------------------------------
# Session bellek (mock). Gerçek sistemde Redis/DB'ye taşınır.
# ---------------------------------------------------------------------------
_SESSIONS: dict[int, dict] = {}

CIKIS_KALIPLARI = re.compile(
    r"^\s*("
    r"iptal|vazgeç|vazgec|iptal et|"
    r"baştan başla|bastan basla|sıfırla|sifirla|"
    r"farklı bir şey(?:\s+sormak)?(?:\s+istiyorum)?|"
    r"farkli bir sey(?:\s+sormak)?(?:\s+istiyorum)?|"
    r"ana menü|ana menu|geri dön|geri don|menü|menu"
    r")\s*[.!]?\s*$",
    re.IGNORECASE,
)

# Intent / hizmet kokusu: isim slotuna düşmemeli (örn. "flo kiralama")
INTENT_KOKUSU = re.compile(
    r"(hastane|sağlık|saglik|otel|turizm|askeri|savunma|eğitim|egitim|"
    r"öğrenci|ogrenci|rezervasyon|randevu|lms|form|sektör|sektor|"
    r"kiralama|kirala|yazılım|yazilim|sistem|platform|teklif|filo|"
    r"araç|arac|çözüm|cozum|yazılımı|yazilimi|"
    r"\?|arıyorum|ariyoruz|istiyorum|istiyoruz|lazım|lazim|gerekiyor)",
    re.IGNORECASE,
)

EMAIL_KALIP = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TELEFON_KALIP = re.compile(r"^(?:\+?90|0)?[\s\-()]*(?:5\d{2}|[2-4]\d{2})[\s\-()]*\d{3}[\s\-()]*\d{2}[\s\-()]*\d{2}$")


def _get_session(session_id: int) -> dict:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            "state": "normal",  # normal | clarification | lead_capture
            "pending_slot": None,  # name | contact | None
            "name": None,
            "contact": None,
            "last_sektor": None,
        }
    return _SESSIONS[session_id]


def reset_session(session_id: int) -> None:
    """Session'ı ana akışa (normal) döndür."""
    _SESSIONS[session_id] = {
        "state": "normal",
        "pending_slot": None,
        "name": None,
        "contact": None,
        "last_sektor": None,
    }


def is_cikis_komutu(mesaj: str) -> bool:
    return bool(CIKIS_KALIPLARI.match((mesaj or "").strip()))


def validate_name_slot(mesaj: str) -> tuple[bool, str]:
    """
    İsim slotu doğrulama (Büyük Filo dersi 1.2).
    Şüpheliyse kabul etme — tekrar sor veya ana akışa bırak.
    """
    m = (mesaj or "").strip()
    if not m:
        return False, "empty"
    if "?" in m or INTENT_KOKUSU.search(m):
        return False, "looks_like_intent"
    kelimeler = m.split()
    if len(m) > 40 or len(kelimeler) > 3:
        return False, "too_long"
    if any(ch.isdigit() for ch in m):
        return False, "has_digit"
    if EMAIL_KALIP.match(m) or TELEFON_KALIP.match(m.replace(" ", "")):
        return False, "looks_like_contact"
    # Sadece harf / Türkçe karakter / boşluk / tire
    if not re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşü\s\-']+", m):
        return False, "invalid_chars"
    return True, "ok"


def validate_contact_slot(mesaj: str) -> tuple[bool, str]:
    m = (mesaj or "").strip()
    if not m:
        return False, "empty"
    if INTENT_KOKUSU.search(m) and not (EMAIL_KALIP.match(m) or "@" in m):
        return False, "looks_like_intent"
    telefon_ok = bool(TELEFON_KALIP.match(re.sub(r"\s+", "", m)))
    email_ok = bool(EMAIL_KALIP.match(m))
    if telefon_ok or email_ok:
        return True, "ok"
    return False, "invalid_format"


# ---------------------------------------------------------------------------
# 1) BOT CEVABI
# ---------------------------------------------------------------------------

def generate_bot_response(intent_sonucu: dict) -> str:
    if intent_sonucu["sektor"] == "belirsiz":
        return (
            "Mesajınızı henüz bir sektör formuyla eşleştiremedim. "
            "Kısaca hangi alanda çözüm aradığınızı yazar mısınız? "
            "(sağlık, turizm, savunma, eğitim) "
            "Vazgeçmek için 'iptal' yazabilirsiniz."
        )

    katman = intent_sonucu.get("katman", "K2")
    return (
        f"Mesajınızı {intent_sonucu['sektor']} sektörüyle eşleştirdim "
        f"(güven: {intent_sonucu['skor']:.2f}, katman: {katman}). "
        f"Form linki: {intent_sonucu['form_url']} "
        f"Başka bir konu için yazmaya devam edebilir veya 'iptal' diyebilirsiniz."
    )


# ---------------------------------------------------------------------------
# 2) KONUŞMA KAYDI (mock — Sinem)
# ---------------------------------------------------------------------------

def save_conversation(
    session_id: int,
    sender_type: str,
    message: str,
    detected_intent_id: int | None = None,
    extra: dict | None = None,
) -> None:
    """
    TODO (Backend / Sinem): SQLAlchemy Konusma kaydı.
    """
    ek = f" | extra={extra}" if extra else ""
    print(
        f"[DB MOCK] session_id={session_id} | {sender_type}: {message!r} "
        f"| intent_id={detected_intent_id} | zaman={datetime.now(timezone.utc).isoformat()}{ek}"
    )


# ---------------------------------------------------------------------------
# 3) STATE'E ÖZEL MANTIK
# ---------------------------------------------------------------------------

def _handle_lead_capture(session: dict, mesaj: str) -> str | None:
    """
    lead_capture state: isim veya iletişim topla.
    Geçersizse slot doldurma; netleştir veya ana akışa bırak.
    Dönüş: cevap metni | None (ana intent akışına devam)
    """
    slot = session.get("pending_slot")

    if slot == "name":
        ok, neden = validate_name_slot(mesaj)
        if ok:
            session["name"] = mesaj.strip()
            session["pending_slot"] = "contact"
            return (
                f"Teşekkürler {session['name']}. "
                "Size dönüş için telefon veya e-posta belirtir misiniz? "
                "(Vazgeçmek için 'iptal' yazın.)"
            )
        if neden == "looks_like_intent":
            # Büyük Filo hatası: "flo kiralama"yı isim sanma
            session["state"] = "normal"
            session["pending_slot"] = None
            return None  # intent akışına düş
        return (
            "Bunu isminiz olarak mı almalıyım, yoksa başka bir sorunuz mu var? "
            "İsimse kısa yazın; soruysa doğrudan yazın. 'iptal' ile çıkabilirsiniz."
        )

    if slot == "contact":
        ok, neden = validate_contact_slot(mesaj)
        if ok:
            session["contact"] = mesaj.strip()
            session["state"] = "normal"
            session["pending_slot"] = None
            return (
                "Bilgilerinizi aldım; ilgili ekip size dönecek. "
                "Yeni bir sektör/form sorusu sorabilirsiniz."
            )
        if neden == "looks_like_intent":
            session["state"] = "normal"
            session["pending_slot"] = None
            return None
        return (
            "Geçerli bir telefon veya e-posta yazar mısınız? "
            "Örn: 05xx xxx xx xx veya ad@sirket.com — 'iptal' ile çıkabilirsiniz."
        )

    return None


def _enter_lead_capture(session: dict) -> str:
    """Clarification sonrası hâlâ belirsizse nazik lead-capture (çıkışlı)."""
    session["state"] = "lead_capture"
    session["pending_slot"] = "name"
    return (
        "Konuyu netleştiremedim. İsterseniz adınızı yazın, sizi uzmanımıza bağlayalım. "
        "Devam etmek istemiyorsanız 'iptal' yazmanız yeterli."
    )


# ---------------------------------------------------------------------------
# 4) ANA AKIŞ
# ---------------------------------------------------------------------------

def handle_user_message(session_id: int, kullanici_mesaji: str) -> str:
    """
    Sıra (kritik):
      1) kullanıcı mesajını kaydet
      2) çıkış komutu? → state=normal, ana menü cevabı
      3) state'e özel slot mantığı (doğrulamalı)
      4) intent tespiti (K1/K2/FB)
      5) form verildiyse state normal kalır (kilit yok)
    """
    session = _get_session(session_id)
    mesaj = (kullanici_mesaji or "").strip()

    save_conversation(session_id=session_id, sender_type="user", message=mesaj)

    # --- 2) Çıkış komutları: HER state'te önce ---
    if is_cikis_komutu(mesaj):
        reset_session(session_id)
        bot_cevabi = (
            "Tamam, başa döndük. Hangi sektörle ilgileniyorsunuz? "
            "(sağlık, turizm, savunma, eğitim)"
        )
        save_conversation(session_id=session_id, sender_type="bot", message=bot_cevabi)
        return bot_cevabi

    # --- 3) State'e özel ---
    if session["state"] == "lead_capture":
        slot_cevap = _handle_lead_capture(session, mesaj)
        if slot_cevap is not None:
            save_conversation(session_id=session_id, sender_type="bot", message=slot_cevap)
            return slot_cevap
        # None → intent kokusu var; aşağıda normal intent'e düş

    # --- 4) Intent (K1/K2/FB) ---
    intent_sonucu = intent_tespit_et(mesaj)

    if intent_sonucu["sektor"] == "belirsiz":
        if session["state"] == "clarification":
            # İkinci belirsiz → çıkışlı lead_capture (kilitlenmeyen FB)
            bot_cevabi = _enter_lead_capture(session)
        else:
            session["state"] = "clarification"
            bot_cevabi = generate_bot_response(intent_sonucu)
    else:
        # Form / sektör eşleşti → kullanıcı kilitlenmez
        session["state"] = "normal"
        session["pending_slot"] = None
        session["last_sektor"] = intent_sonucu["sektor"]
        bot_cevabi = generate_bot_response(intent_sonucu)

    save_conversation(
        session_id=session_id,
        sender_type="bot",
        message=bot_cevabi,
        detected_intent_id=None,
        extra={
            "state": session["state"],
            "sektor": intent_sonucu["sektor"],
            "katman": intent_sonucu.get("katman"),
            "skor": intent_sonucu.get("skor"),
        },
    )
    return bot_cevabi


# ---------------------------------------------------------------------------
# 5) DEMO — Büyük Filo tuzak senaryoları
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Model: {MODEL_ADI} | Eşik: {SIMILARITY_ESIK}")
    print(f"Sektörler: {', '.join(SEKTOR_REFERANSLARI.keys())}\n")

    sid = 101
    reset_session(sid)

    senaryo = [
        ("hastane yönetim sistemleri arıyoruz", "K1/K2 form"),
        ("iptal", "cikis komutu"),
        ("fiyat teklifi almak istiyorum", "FB clarification"),
        ("fiyat teklifi", "2. belirsiz lead_capture"),
        ("flo kiralama", "slot reddi / intent kokusu"),
        ("iptal", "lead_capture cikis"),
        ("sğlk poliklinik randevu", "kisaltma"),
        ("3 yıllık otel rezervasyon ve check-in platformu istiyoruz", "uzun kurumsal"),
        ("sağlık", "determinizm-1"),
        ("sağlık", "determinizm-2"),
    ]

    for mesaj, not_ in senaryo:
        print(f"\n--- [{not_}] Kullanıcı: {mesaj}")
        print(f"--- Bot: {handle_user_message(sid, mesaj)}")
        print(f"    state={_get_session(sid)['state']}")
