import sys
from pathlib import Path
import json
import numpy as np
from sqlalchemy import text
import sys

# Proje kök dizinini Python path'e ekle
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db.connection import get_engine

def main():
    dataset_path = ROOT / "data" / "raw" / "chatbot_dataset.json"
    npz_path = ROOT / "data" / "processed" / "embeddings.npz"

    print(f"Reading dataset from {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        records = data.get("kayitlar", [])

    print(f"Reading embeddings from {npz_path}")
    npz_data = np.load(npz_path)
    embeddings = npz_data["vectors"]

    if len(records) != len(embeddings):
        print(f"Hata: JSON'da {len(records)} kayıt var, ama NPZ'de {len(embeddings)} vektör var!")
        sys.exit(1)

    print(f"JSON records: {len(records)} | NPZ vectors: {len(embeddings)}")

    engine = get_engine()

    with engine.begin() as conn:
        print("TRUNCATE qa_embeddings tablosu temizleniyor...")
        conn.execute(text("TRUNCATE TABLE qa_embeddings RESTART IDENTITY CASCADE"))

        print("Kayıtlar veritabanına ekleniyor...")
        for i, rec in enumerate(records):
            question = rec.get("mesaj", "").strip()
            if not question:
                continue
                
            # Eğer cevap yoksa zorunlu kolon için placeholder
            answer = rec.get("cevap", "Sistem yanıtı bulunamadı.")
            if not answer.strip():
                answer = "Sistem yanıtı bulunamadı."
                
            sektor = rec.get("beklenen_sektor", "belirsiz")
            mod = rec.get("beklenen_mod", "FB")
            intent_code = f"{sektor}/{mod}" if sektor != "belirsiz" else "ood"

            # intent_id'yi bul veya oluştur
            res = conn.execute(text("""
                INSERT INTO intents (intent_code, url) 
                VALUES (:ic, :url) 
                ON CONFLICT (intent_code) DO UPDATE SET url = EXCLUDED.url
                RETURNING id
            """), {"ic": intent_code, "url": f"http://internal/{sektor}"})
            
            intent_id = res.scalar()
            
            emb = embeddings[i].tolist()

            conn.execute(text("""
                INSERT INTO qa_embeddings (question, answer, intent_id, embedding, is_augmented)
                VALUES (:q, :a, :iid, :emb, false)
            """), {
                "q": question,
                "a": answer,
                "iid": intent_id,
                "emb": emb
            })
            
        count = conn.execute(text("SELECT COUNT(*) FROM qa_embeddings")).scalar()
        print(f"\n=========================================")
        print(f"BAŞARILI: qa_embeddings tablosunda TAM {count} kayıt var!")
        print(f"=========================================\n")

if __name__ == "__main__":
    main()
