import json
import os
import random
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.services.dataset_ids import compute_next_record_id
from app.services.index_sync import sync_new_qa_records

router = APIRouter(prefix="/admin", tags=["admin"])

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
AUGMENTED_DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"


class AddQaRequest(BaseModel):
    query: str
    answer: str
    sector: str
    augment: bool = False


def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    token = os.getenv("ADMIN_API_TOKEN", "super-secret")
    if not auth_header or auth_header != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


SYNONYMS = {
    "müşteri": ["kullanıcı", "tüketici", "hedef kitle"],
    "veritabanı": ["veri havuzu", "data merkezi"],
    "veritabanımız": ["veri sistemimiz", "data yapımız"],
    "güvenli": ["korumalı", "şifreli", "yüksek güvenlikli"],
    "bulut": ["cloud", "sanal sunucu"],
    "altyapı": ["sistem", "mimari", "platform"],
    "altyapısı": ["sistemi", "mimarisi", "çözümü"],
    "altyapısını": ["sistemini", "mimarisini"],
    "kurmak": ["inşa etmek", "geçiş yapmak", "entegre etmek"],
    "istiyoruz": ["talep etmekteyiz", "ihtiyacımız bulunuyor", "planlıyoruz"],
    "lazım": ["gerekli", "ihtiyaç duyuyoruz", "şart"],
    "otel": ["konaklama tesisi", "tatil merkezi"],
    "rezervasyon": ["yer ayırtma", "booking"],
    "hasta": ["danışan", "tedavi gören"],
    "hastane": ["sağlık tesisi", "klinik"],
    "yazılım": ["uygulama", "otomasyon", "dijital çözüm"],
    "yazılımı": ["uygulaması", "sistemi"],
    "eğitim": ["ders", "kurs", "öğrenim"],
    "öğrenci": ["kursiyer", "katılımcı"],
    "bilet": ["giriş kartı", "geçiş hakkı"],
    "konser": ["etkinlik", "canlı performans"],
    "fiyat": ["ücret", "maliyet", "teklif"],
    "yardım": ["destek", "danışmanlık"],
    "merhaba": ["selamlar", "iyi günler"],
}

TEMPLATES = [
    "Kurumumuzun dijital dönüşüm süreçlerinde {core} konularında profesyonel bir yaklaşım aramaktayız, süreç nasıl ilerliyor?",
    "Ekiplerimizin verimliliğini artırmak adına acilen {core} odaklı yeni bir sisteme geçiş yapmayı planlıyoruz.",
    "Acaba {core} ihtiyaçlarımız için bize ne tür alternatifler sunabilirsiniz, detaylı bir fiyatlandırma alabilir miyim?",
    "Mevcut işleyişimizi hızlandırmak maksadıyla {core} alanında kalıcı ve güvenilir bir partner arayışındayız.",
    "Operasyonel maliyetlerimizi düşürmek ve {core} standartlarımızı yükseltmek için acil olarak desteğinize ihtiyacımız var.",
]


def synonymize(word: str) -> str:
    w = word.lower()
    for k, v in SYNONYMS.items():
        if w == k:
            return random.choice(v)
    return word


def compute_overlap(text1: str, text2: str) -> float:
    set1 = set(re.findall(r"\w+", text1.lower()))
    set2 = set(re.findall(r"\w+", text2.lower()))
    if not set2:
        return 0.0
    return len(set1 & set2) / len(set2)


def generate_variations(text: str, count: int = 3) -> list[str]:
    stop_words = {
        "için", "gibi", "ile", "veya", "olmak", "etmek", "yapmak", "neden", "nasıl",
        "hangi", "göre", "taraf", "daha", "bizim", "bize", "sizin", "size", "olarak",
    }
    words = re.findall(r"\w+", text)
    long_words = [w for w in words if len(w) > 3 and w.lower() not in stop_words]

    variations = []
    attempts = 0
    while len(variations) < count and attempts < 20:
        attempts += 1

        sample_size = min(random.randint(1, 2), len(long_words)) if long_words else 0
        if sample_size > 0:
            core_sample = random.sample(long_words, sample_size)
            transformed_core = " ve ".join([synonymize(w) for w in core_sample])
        else:
            transformed_core = synonymize(text.split()[0]) if text else "süreç"

        template = random.choice(TEMPLATES)
        candidate = template.format(core=transformed_core)
        candidate = re.sub(r"\s+", " ", candidate).strip()

        if compute_overlap(candidate, text) < 0.50:
            is_unique = True
            for v in variations:
                if compute_overlap(candidate, v) > 0.60:
                    is_unique = False
                    break
            if is_unique:
                variations.append(candidate)

    return variations


@router.post("/add_qa")
def add_qa(req: AddQaRequest, bg_tasks: BackgroundTasks, _=Depends(verify_token)):
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("kayitlar", [])
    aug_records: list[dict] = []
    if AUGMENTED_DATASET_PATH.exists():
        with open(AUGMENTED_DATASET_PATH, "r", encoding="utf-8") as f:
            aug_records = json.load(f).get("kayitlar", [])

    max_id = compute_next_record_id(records, aug_records)

    new_records = []
    new_records.append({
        "id": max_id,
        "kaynak": "admin_panel",
        "mesaj": req.query,
        "cevap": req.answer,
        "is_augmented": False,
        "beklenen_sektor": req.sector,
        "beklenen_mod": "K2",
        "zorluk": "uzun_kurumsal",
    })

    generated = []
    if req.augment:
        vars_list = generate_variations(req.query, count=3)
        for v in vars_list:
            max_id += 1
            new_records.append({
                "id": max_id,
                "kaynak": "admin_panel_augmented",
                "mesaj": v,
                "cevap": req.answer,
                "is_augmented": True,
                "beklenen_sektor": req.sector,
                "beklenen_mod": "K2",
                "zorluk": "uzun_kurumsal",
            })
            generated.append(v)

    records.extend(new_records)
    data["kayitlar"] = records

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if AUGMENTED_DATASET_PATH.exists():
        with open(AUGMENTED_DATASET_PATH, "r", encoding="utf-8") as f:
            aug_data = json.load(f)

        aug_records = aug_data.get("kayitlar", [])
        aug_records.extend(new_records)
        aug_data["kayitlar"] = aug_records

        with open(AUGMENTED_DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump(aug_data, f, ensure_ascii=False, indent=2)

    bg_tasks.add_task(sync_new_qa_records, new_records)

    return {
        "status": "success",
        "message": f"{len(new_records)} kayıt eklendi, index arka planda güncelleniyor.",
        "original": req.query,
        "augmented_variations": generated,
    }
