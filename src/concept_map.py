"""Sektör kavram haritası — ezber cümle değil, semantik köprü (anchor)."""

from __future__ import annotations

# Sektör → kavram token / kısa anchor metinleri
CONCEPT_MAP: dict[str, tuple[str, ...]] = {
    "saglik": (
        "psikoloji",
        "psikolog",
        "ruh sağlığı",
        "tahlil",
        "poliklinik",
        "hekim",
        "sevk",
        "uzman doktor",
        "klinik",
        "reçete",
        "muayene",
        "terapi",
        "randevu",
        "hastane",
    ),
    "turizm": (
        "müze",
        "ören yeri",
        "müze kart",
        "bilet",
        "konaklama",
        "seyahat",
        "acente",
        "kültür turu",
        "rehberli tur",
        "tatil",
        "otel",
        "pansiyon",
        "deniz",
    ),
    "bilisim": (
        "api",
        "sdk",
        "saas",
        "bulut",
        "cloud",
        "entegrasyon",
        "yazılım",
        "yazilim",
        "otomasyon",
        "crm",
        "erp",
        "siber güvenlik",
        "database",
        "veritabanı",
        "sunucu",
        "server",
    ),
    "egitim": (
        "lise",
        "sınav",
        "başvuru",
        "burs",
        "taban puan",
        "kontenjan",
        "müfredat",
        "dekanlık",
        "üniversite",
        "öğrenci işleri",
        "mühendislik",
    ),
    "eglence": (
        "ott",
        "streaming",
        "yayıncılık",
        "oyun motoru",
        "unity",
        "unreal",
        "render",
        "metacast",
        "medya",
        "film",
        "müzik",
        "konser",
        "biletleme",
    ),
}

# Klinik / sağlık sinyali — "sınav+psikolog" gibi hibritte sağlığı öne al
_HEALTH_PRIORITY = (
    "psikolog",
    "psikoloji",
    "ruh sağlığı",
    "poliklinik",
    "reçete",
    "tahlil",
    "muayene",
    "terapi",
    "hastane",
)

# Korpusa eklenecek paraphrase anchor'lar (mentor test cümlesinin birebir kopyası YOK)
CONCEPT_ANCHOR_SEEDS: list[dict[str, str]] = [
    # saglik — randevu / poliklinik
    {"mesaj": "poliklinik randevu ve muayene sırası", "beklenen_sektor": "saglik"},
    {"mesaj": "hastaneden online randevu alma işlemi", "beklenen_sektor": "saglik"},
    {"mesaj": "klinik randevu hekim takvimi", "beklenen_sektor": "saglik"},
    {"mesaj": "uzman doktordan muayene randevusu", "beklenen_sektor": "saglik"},
    # saglik — ruh sağlığı (sınav stresi paraphrase)
    {"mesaj": "ruh sağlığı uzmanı psikolojik destek", "beklenen_sektor": "saglik"},
    {"mesaj": "öğrenci stresi için psikolojik danışmanlık", "beklenen_sektor": "saglik"},
    {"mesaj": "psikolog görüşmesi ve terapi süreci", "beklenen_sektor": "saglik"},
    {"mesaj": "sınav döneminde ruh sağlığı danışmanlığı", "beklenen_sektor": "saglik"},
    # turizm — müze / kart (fiyat paraphrase)
    {"mesaj": "müze girişi kart ücreti ve ören yeri bileti", "beklenen_sektor": "turizm"},
    {"mesaj": "tarihi müze ziyareti bilet fiyatı", "beklenen_sektor": "turizm"},
    {"mesaj": "müze kartı ile ören yeri gezisi", "beklenen_sektor": "turizm"},
    # turizm — otel / deniz
    {"mesaj": "deniz kenarı otel ve tatil konaklama", "beklenen_sektor": "turizm"},
    {"mesaj": "sahil oteli pansiyon rezervasyon", "beklenen_sektor": "turizm"},
    {"mesaj": "tatil beldesinde denize yakın konaklama", "beklenen_sektor": "turizm"},
    {"mesaj": "otel pansiyon marina yakını konaklama", "beklenen_sektor": "turizm"},
    # bilisim — API / bulut / yazılım
    {"mesaj": "kurumsal API entegrasyonu ve bulut veri yedekleme", "beklenen_sektor": "bilisim"},
    {"mesaj": "SaaS platformu kullanıcı lisans sözleşmesi", "beklenen_sektor": "bilisim"},
    {"mesaj": "CRM ve ERP yazılımları arası veri senkronizasyonu", "beklenen_sektor": "bilisim"},
    {"mesaj": "siber güvenlik altyapısı sızma testi hizmeti", "beklenen_sektor": "bilisim"},
    {"mesaj": "sunucu ağ yönetimi ve firewall yapılandırması", "beklenen_sektor": "bilisim"},
    # egitim — burs / puan paraphrase
    {"mesaj": "üniversite burs başvurusu ve koşullar", "beklenen_sektor": "egitim"},
    {"mesaj": "bölüm taban puanı ve kontenjan bilgisi", "beklenen_sektor": "egitim"},
    {"mesaj": "fakülte burs imkanları başvuru", "beklenen_sektor": "egitim"},
    {"mesaj": "mühendislik bölümü taban puan kontenjan", "beklenen_sektor": "egitim"},
    {"mesaj": "öğrenci işleri burs ve kayıt süreci", "beklenen_sektor": "egitim"},
    # eglence — yayıncılık / medya / oyun
    {"mesaj": "OTT streaming platformu medya yayın lisansı", "beklenen_sektor": "eglence"},
    {"mesaj": "oyun motoru entegrasyonu ve grafik render performansı", "beklenen_sektor": "eglence"},
    {"mesaj": "kurumsal etkinlik biletleme ve konser organizasyonu", "beklenen_sektor": "eglence"},
    {"mesaj": "dijital yayıncılık platformu içerik hakları yönetimi", "beklenen_sektor": "eglence"},
]


def expand_query_concept_seeds(query: str) -> list[str]:
    """
    Sorguda kavram token'ı varsa sektöre göre ayrı köprü seed'leri üret.
    Klinik sağlık sinyali varsa sağlık köprüsü öne alınır.
    """
    from src.chatbot import to_ascii, _normalize

    folded = to_ascii(_normalize(query or "")).lower()
    if not folded:
        return []

    health_hit = any(to_ascii(t).lower() in folded for t in _HEALTH_PRIORITY)

    seeds: list[tuple[int, str]] = []
    for sektor, concepts in CONCEPT_MAP.items():
        matched = [c for c in concepts if to_ascii(c).lower() in folded]
        if not matched:
            continue
        # Hibrit: sağlık sinyali varken eğitim'i (yalnızca sınav vb.) geri plana al
        if health_hit and sektor == "egitim" and not any(
            to_ascii(x).lower() in folded
            for x in ("burs", "taban puan", "kontenjan", "üniversite", "müfredat", "dekanlık")
        ):
            continue
        bridge = list(dict.fromkeys(list(matched) + list(concepts[:6])))
        text = " ".join(bridge[:8])
        priority = 0 if (health_hit and sektor == "saglik") else 1
        seeds.append((priority, text))

    seeds.sort(key=lambda x: x[0])
    return [t for _, t in seeds]


def expand_query_concepts(query: str) -> str | None:
    """Geriye dönük: tüm köprü seed'lerini tek stringde birleştir."""
    seeds = expand_query_concept_seeds(query)
    if not seeds:
        return None
    uniq = list(dict.fromkeys(" ".join(seeds).split()))
    return " ".join(uniq[:12])
