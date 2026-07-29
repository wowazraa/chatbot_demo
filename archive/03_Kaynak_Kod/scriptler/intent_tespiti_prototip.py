"""
Intent Tespiti / Sektör Sınıflandırma Prototipi
=================================================
Model: paraphrase-multilingual-MiniLM-L12-v2 (384 boyut)

Katmanlar (Büyük Filo K1→K2→FB ilhamı):
  K1  fast path  — bariz anahtar kelime / kısaltma → embedding yok
  K2  embedding  — cosine similarity + eşik
  FB  belirsiz   — skor eşiğin altında

Dersler:
  - Referans metinler sektöre özgü ve birbirinden ayrışık olmalı
  - Kısaltma/yazım gürültüsü normalize edilmeli
"""

from __future__ import annotations

import re

from sentence_transformers import SentenceTransformer, util

MODEL_ADI = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_ESIK = 0.50  # TODO: toplantı sonrası netleştir

# ---------------------------------------------------------------------------
# Sektör referansları — genel kelimeler ("sistem", "teknoloji") yerine
# sektöre özgü ayırt edici ifadeler (Büyük Filo dersi 1.5)
# ---------------------------------------------------------------------------
SEKTOR_REFERANSLARI = {
    "sağlık": {
        "ornek_metin": (
            "Hastane ve klinik: hasta kaydı, poliklinik randevu, tıbbi görüntü "
            "arşivi, teletıp, laboratuvar sonuçları, acil servis triaj."
        ),
        "form_url": "https://ornek-domain.com/form/saglik",
        "anahtarlar": (
            "sağlık", "hastane", "hasta", "poliklinik", "randevu", "teletıp",
            "tıbbi", "klinik", "ambulans", "112", "pacs", "laboratuvar",
        ),
    },
    "turizm": {
        "ornek_metin": (
            "Otel ve seyahat: oda rezervasyon, müsaitlik, check-in, paket tur, "
            "seyahat acentesi, havayolu bilet, konaklama envanteri."
        ),
        "form_url": "https://ornek-domain.com/form/turizm",
        "anahtarlar": (
            "turizm", "otel", "rezervasyon", "konaklama", "check-in", "checkin",
            "paket tur", "seyahat", "oda", "misafir", "havayolu",
        ),
    },
    "savunma": {
        "ornek_metin": (
            "Askeri ve savunma: kriptolu haberleşme, komuta kontrol, radar "
            "tehdit izleme, birlik mesajlaşma, kritik altyapı siber güvenlik."
        ),
        "form_url": "https://ornek-domain.com/form/savunma",
        "anahtarlar": (
            "savunma", "askeri", "birlik", "komuta", "kontrol", "radar",
            "kriptolu", "haberleşme", "siber güvenlik", "tehdit",
        ),
    },
    "eğitim": {
        "ornek_metin": (
            "Okul ve kampüs: uzaktan eğitim, LMS, öğrenci bilgi sistemi, "
            "sınav otomasyonu, veli-öğretmen iletişim, ödev takip."
        ),
        "form_url": "https://ornek-domain.com/form/egitim",
        "anahtarlar": (
            "eğitim", "okul", "öğrenci", "lms", "uzaktan eğitim", "sınav",
            "veli", "öğretmen", "kampüs", "ders", "ödev",
        ),
    },
}

# Kısaltma / yaygın yazım → açılım (Büyük Filo dersi 1.4)
KISALTMA_HARITASI: dict[str, str] = {
    r"\bsğlk\b": "sağlık",
    r"\bsaglik\b": "sağlık",
    r"\btrzm\b": "turizm",
    r"\botl\b": "otel",
    r"\bsvnma\b": "savunma",
    r"\bask\b": "askeri",
    r"\begtm\b": "eğitim",
    r"\begitim\b": "eğitim",
    r"\buniv\b": "üniversite",
    r"\brzv\b": "rezervasyon",
    r"\bhstn\b": "hastane",
}

_FAZLA_BOSLUK = re.compile(r"\s+")


def get_sektor_referanslari() -> dict:
    """Sektör → referans metin / form_url / anahtarlar (tek kaynak erişimi)."""
    return SEKTOR_REFERANSLARI


def normalize_mesaj(mesaj: str) -> str:
    """Kısaltma ve yazım gürültüsünü aç; embedding öncesi sadeleştir."""
    metin = (mesaj or "").strip().lower()
    for pattern, repl in KISALTMA_HARITASI.items():
        metin = re.sub(pattern, repl, metin, flags=re.IGNORECASE)
    return _FAZLA_BOSLUK.sub(" ", metin).strip()


def _fast_path(mesaj_norm: str) -> dict | None:
    """
    K1: Mesajda tek bir sektöre ait belirgin anahtar varsa embedding'e gitme.
    Birden fazla sektöre anahtar düşerse None dön (K2'ye bırak).
    """
    eslesen: list[str] = []
    for sektor, bilgi in SEKTOR_REFERANSLARI.items():
        for anahtar in bilgi["anahtarlar"]:
            if anahtar.lower() in mesaj_norm:
                eslesen.append(sektor)
                break
    if len(eslesen) == 1:
        sektor = eslesen[0]
        return {
            "mesaj": mesaj_norm,
            "sektor": sektor,
            "form_url": SEKTOR_REFERANSLARI[sektor]["form_url"],
            "skor": 1.0,
            "katman": "K1",
        }
    return None


# ---------------------------------------------------------------------------
# Model + referans embedding (K2)
# ---------------------------------------------------------------------------
model = SentenceTransformer(MODEL_ADI)

sektor_isimleri = list(SEKTOR_REFERANSLARI.keys())
referans_metinler = [SEKTOR_REFERANSLARI[s]["ornek_metin"] for s in sektor_isimleri]
referans_embeddingler = model.encode(referans_metinler, convert_to_tensor=True)


def referans_arasi_benzerlik() -> list[tuple[str, str, float]]:
    """İki referans metni >0.70 ise yeniden yazılmalı (ders 1.5 kontrolü)."""
    mat = util.cos_sim(referans_embeddingler, referans_embeddingler)
    ciftler = []
    for i in range(len(sektor_isimleri)):
        for j in range(i + 1, len(sektor_isimleri)):
            skor = float(mat[i][j])
            ciftler.append((sektor_isimleri[i], sektor_isimleri[j], round(skor, 4)))
    return sorted(ciftler, key=lambda x: x[2], reverse=True)


def intent_tespit_et(mesaj: str, *, fast_path: bool = True) -> dict:
    """
    Kullanıcı mesajını sektörlere göre sınıflandırır.

    Dönüş: mesaj, sektor, form_url, skor, katman (K1|K2|FB)
    """
    ham = (mesaj or "").strip()
    mesaj_norm = normalize_mesaj(ham)

    if fast_path:
        hizli = _fast_path(mesaj_norm)
        if hizli is not None:
            hizli["mesaj"] = ham
            hizli["normalize_mesaj"] = mesaj_norm
            return hizli

    mesaj_embedding = model.encode(mesaj_norm, convert_to_tensor=True)
    skorlar = util.cos_sim(mesaj_embedding, referans_embeddingler)[0]

    en_yuksek_index = int(skorlar.argmax())
    en_yuksek_skor = float(skorlar[en_yuksek_index])

    if en_yuksek_skor < SIMILARITY_ESIK:
        return {
            "mesaj": ham,
            "normalize_mesaj": mesaj_norm,
            "sektor": "belirsiz",
            "form_url": None,
            "skor": round(en_yuksek_skor, 4),
            "katman": "FB",
        }

    sektor = sektor_isimleri[en_yuksek_index]
    return {
        "mesaj": ham,
        "normalize_mesaj": mesaj_norm,
        "sektor": sektor,
        "form_url": SEKTOR_REFERANSLARI[sektor]["form_url"],
        "skor": round(en_yuksek_skor, 4),
        "katman": "K2",
    }


if __name__ == "__main__":
    print(f"Model yüklendi: {MODEL_ADI}")
    print("\nReferanslar arası benzerlik (yüksek = karışma riski):")
    for a, b, s in referans_arasi_benzerlik():
        uyari = " ⚠ YAKIN" if s > 0.70 else ""
        print(f"  {a} ↔ {b}: {s}{uyari}")

    test_mesajlari = [
        "sağlık",  # K1
        "sğlk hastane yazılımı",  # kısaltma
        "3 yıllık otel rezervasyon ve oda envanter platformu istiyoruz",  # uzun
        "askeri haberleşme çözümleri lazım",
        "uzaktan eğitim platformu istiyoruz",
        "bugün hava çok güzeldi",
        "sağlık",
        "sağlık",  # determinizm kontrolü
    ]
    print(f"\nEşik: {SIMILARITY_ESIK}\n")
    onceki = None
    for mesaj in test_mesajlari:
        s = intent_tespit_et(mesaj)
        print(
            f"[{s['katman']}] {mesaj!r} → {s['sektor']} | skor={s['skor']} | {s['form_url']}"
        )
        if mesaj == "sağlık" and onceki is not None:
            assert s["skor"] == onceki["skor"] and s["sektor"] == onceki["sektor"]
            print("  ✓ determinizm OK")
        if mesaj == "sağlık":
            onceki = s
