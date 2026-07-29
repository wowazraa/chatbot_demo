import sys
import os
import json
import numpy as np
from pathlib import Path

# Script dizininden chatbot_demo klasörüne ulaşım
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db_api.bridge import SessionLocal, Sector, Intent, QaEmbedding

def migrate():
    db = SessionLocal()
    try:
        print("[1] Seeding Sectors...")
        sectors_data = [
            ("saglik", "Sağlık", "Health"),
            ("turizm", "Turizm", "Tourism"),
            ("egitim", "Eğitim", "Education"),
            ("bilisim", "Bilişim", "IT/Bilişim"),
            ("eglence", "Eğlence", "Entertainment"),
            ("ood", "OOD", "Out of Domain")
        ]
        sector_map = {}
        for key, tr, en in sectors_data:
            sector = db.query(Sector).filter_by(sector_key=key).first()
            if not sector:
                sector = Sector(sector_key=key, sector_name_tr=tr, sector_name_en=en)
                db.add(sector)
                db.flush()
            else:
                sector.sector_name_tr = tr
                sector.sector_name_en = en
            sector_map[key] = sector.id

        print("[2] Seeding Intents...")
        intents_data = [
            ("health_appointment", "https://example.com/forms/health", "Sağlık randevu formu"),
            ("tourism_hotel", "https://example.com/forms/tourism", "Turizm konaklama formu"),
            ("education_enrollment", "https://example.com/forms/education", "Eğitim kayıt formu"),
            ("bilisim_integration", "https://example.com/forms/it", "Bilişim entegrasyon formu"),
            ("eglence_streaming", "https://example.com/forms/entertainment", "Eğlence yayın formu"),
            ("sector_form_request", "https://example.com/forms/sector", "Genel sektör formu")
        ]
        
        sector_to_intent = {
            "saglik": "health_appointment",
            "turizm": "tourism_hotel",
            "egitim": "education_enrollment",
            "bilisim": "bilisim_integration",
            "eglence": "eglence_streaming",
            "ood": "sector_form_request"
        }
        
        intent_map = {}
        for code, url, desc in intents_data:
            intent = db.query(Intent).filter_by(intent_code=code).first()
            if not intent:
                intent = Intent(intent_code=code, url=url, description=desc)
                db.add(intent)
                db.flush()
            else:
                intent.url = url
                intent.description = desc
            intent_map[code] = intent.id

        print("[3] Clearing existing QA embeddings...")
        db.query(QaEmbedding).delete()
        db.flush()

        print("[4] Loading index files...")
        npz_path = ROOT / "data" / "processed" / "embeddings.npz"
        meta_path = ROOT / "data" / "processed" / "index_meta.json"
        
        if not npz_path.exists() or not meta_path.exists():
            print("[!] Hata: data/processed/ altında embeddings.npz veya index_meta.json bulunamadı!")
            print("Lütfen önce 'python scripts/build_index.py' çalıştırarak indeksi oluşturun.")
            return

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
            
        npz = np.load(npz_path)
        vectors = npz["vectors"]
        
        texts = meta_data["texts"]
        metas = meta_data["meta"]
        
        print(f"Total texts: {len(texts)}")
        print(f"Total vectors: {len(vectors)}")
        
        assert len(texts) == len(vectors), "Mismatch between texts and vectors length!"
        
        print("[5] Inserting actual records...")
        inserted_count = 0
        for i in range(len(texts)):
            question = texts[i]
            meta = metas[i]
            vector = list(map(float, vectors[i]))
            
            sector_key = meta.get("beklenen_sektor")
            if sector_key == "belirsiz" or not sector_key:
                sector_key = "ood"
                
            intent_code = sector_to_intent.get(sector_key, "sector_form_request")
            intent_id = intent_map[intent_code]
            
            is_augmented = meta.get("zorluk", "").startswith("augmented")
            answer = f"Talebiniz {sector_key} sektörüyle ilişkilendirildi."
            
            qa_rec = QaEmbedding(
                question=question,
                answer=answer,
                intent_id=intent_id,
                is_augmented=is_augmented,
                embedding=vector
            )
            db.add(qa_rec)
            inserted_count += 1
            if inserted_count % 300 == 0:
                print(f"Inserted {inserted_count} records...")
                
        db.commit()
        print(f"[OK] Successfully migrated {inserted_count} records to PostgreSQL!")
        
    except Exception as e:
        db.rollback()
        print(f"[Error] Migration failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
