import json
import os
import random
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from src.db.connection import get_engine
from src.db.npz_store import NpzDenseStore
from scripts.build_index import build as build_index
from scripts.seed_pgvector import seed_db as seed_pgvector
import psycopg2
from src.embedder import BGEEmbedder

router = APIRouter(prefix="/admin", tags=["admin"])

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"

class AddQaRequest(BaseModel):
    query: str
    sector: str
    augment: bool = False

def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    token = os.getenv("ADMIN_API_TOKEN", "super-secret")
    if not auth_header or auth_header != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")

def background_sync_index():
    print("[Background] Starting index rebuild...")
    build_index(use_raw=True, batch_size=64)
    print("[Background] Starting database seed...")
    seed_pgvector(truncate=True)
    print("[Background] Sync complete.")

def background_sync_allintos(new_records):
    if os.getenv("ALLINTOS_DB_ENABLED", "false").lower() != "true":
        print("[Allintos] ALLINTOS_DB_ENABLED=false, skipping DB insertion.")
        return
        
    db_url = os.getenv("ALLINTOS_DB_URL")
    if not db_url:
        print("[Allintos] ALLINTOS_DB_URL missing, skipping DB insertion.")
        return
        
    print(f"[Allintos] Inserting {len(new_records)} records into Allintos DB...")
    
    embedder = BGEEmbedder()
    try:
        # sqlalchemy URL'si verilmişse psycopg2'ye uyarla
        conn_str = db_url.replace("postgresql+psycopg2://", "postgresql://")
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        for rec in new_records:
            mesaj = rec["mesaj"]
            sektor = rec["beklenen_sektor"]
            emb = embedder.embed(mesaj).tolist()
            
            cur.execute("""
                INSERT INTO chatbot_demo_qa_embeddings (mesaj, beklenen_sektor, embedding)
                VALUES (%s, %s, %s)
            """, (mesaj, sektor, str(emb)))
            
        conn.commit()
        cur.close()
        conn.close()
        print("[Allintos] Sync complete.")
    except Exception as e:
        print(f"[Allintos] Failed to insert records: {e}")

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
    # 1. Anlamsız bağlaç ve yardımcı fiilleri filtrele
    stop_words = {"için", "gibi", "ile", "veya", "olmak", "etmek", "yapmak", "neden", "nasıl", "hangi", "göre", "taraf", "daha", "bizim", "bize", "sizin", "size", "olarak"}
    words = re.findall(r"\w+", text)
    long_words = [w for w in words if len(w) > 3 and w.lower() not in stop_words]
    
    variations = []
    attempts = 0
    while len(variations) < count and attempts < 20:
        attempts += 1
        
        # Sadece anlamlı 1-2 kelimeyi merkeze al
        sample_size = min(random.randint(1, 2), len(long_words)) if long_words else 0
        if sample_size > 0:
            core_sample = random.sample(long_words, sample_size)
            transformed_core = " ve ".join([synonymize(w) for w in core_sample])
        else:
            transformed_core = synonymize(text.split()[0]) if text else "süreç"
            
        template = random.choice(TEMPLATES)
        candidate = template.format(core=transformed_core)
        
        # Cümleyi biraz daha doğal hale getirmek için çift boşlukları vs. düzelt
        candidate = re.sub(r"\s+", " ", candidate).strip()
        
        # Check overlap against original
        if compute_overlap(candidate, text) < 0.50:
            # Also check diversity among variations
            is_unique = True
            for v in variations:
                if compute_overlap(candidate, v) > 0.60:
                    is_unique = False
                    break
            if is_unique:
                variations.append(candidate)
                
    return variations

@router.post("/add_qa")
def add_qa(req: AddQaRequest, bg_tasks: BackgroundTasks, _ = Depends(verify_token)):
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = data.get("kayitlar", [])
    max_id = max([r.get("id", 0) for r in records], default=0)
    
    # 1. Ekle (Orijinal)
    new_records = []
    max_id += 1
    new_records.append({
        "id": max_id,
        "kaynak": "admin_panel",
        "mesaj": req.query,
        "beklenen_sektor": req.sector,
        "beklenen_mod": "K2",
        "zorluk": "uzun_kurumsal"
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
                "beklenen_sektor": req.sector,
                "beklenen_mod": "K2",
                "zorluk": "uzun_kurumsal"
            })
            generated.append(v)
            
    records.extend(new_records)
    data["kayitlar"] = records
    
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    bg_tasks.add_task(background_sync_index)
    bg_tasks.add_task(background_sync_allintos, new_records)
    
    return {
        "status": "success",
        "message": f"{len(new_records)} kayıt eklendi, index arka planda güncelleniyor.",
        "original": req.query,
        "augmented_variations": generated
    }
