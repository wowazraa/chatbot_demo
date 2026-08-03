import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from sqlalchemy import text
from app.db.connection import get_engine
from app.db.npz_store import NpzDenseStore

def seed_db(truncate: bool = False):
    engine = get_engine()
    
    print("Loading vectors from NPZ...")
    store = NpzDenseStore()
    vectors = store._vectors
    texts = store._texts
    meta = store._meta
    
    total = len(texts)
    print(f"Loaded {total} records from embeddings.npz.")
    
    with engine.begin() as conn:
        if truncate:
            print("Truncating table vector_index...")
            conn.execute(text("TRUNCATE TABLE vector_index RESTART IDENTITY CASCADE"))
            
        print("Inserting records into PostgreSQL vector_index...")
        inserted = 0
        for i in range(total):
            m = meta[i]
            v = vectors[i]
            
            # pgvector requires a string representation of the array e.g., '[0.1, 0.2, ...]'
            vec_str = "[" + ",".join(str(x) for x in v.tolist()) + "]"
            
            # Use 'source_id' if available, otherwise generate one
            source_id = str(m.get("source_id") or m.get("id") or f"gen_{i}")
            
            # v2_pipeline map_sector expects 'bilisim', not 'bilisim_integration'
            # intent_code is 'bilisim_integration', but beklenen_sektor is 'bilisim'
            raw_sec = str(m.get("beklenen_sektor") or "ood").lower().strip()
            
            # Simple normalization mapping to avoid importing from chatbot
            sec_map = {
                "sağlık": "saglik", "eğitim": "egitim", "bilişim": "bilisim", 
                "eğlence": "eglence", "turizm": "turizm",
                "health": "saglik", "education": "egitim", "it": "bilisim",
                "entertainment": "eglence", "hospitality": "turizm"
            }
            sector = sec_map.get(raw_sec, raw_sec)
            if sector not in ["saglik", "turizm", "egitim", "bilisim", "eglence"]:
                sector = "ood"
                
            sub_intent = m.get("intent_code", "none")
            lang = m.get("lang", "tr")
            
            conn.execute(text("""
                INSERT INTO vector_index (source_id, sector, sub_intent, text_content, embedding, lang)
                VALUES (:sid, :sec, :sub, :txt, :emb, :lang)
                ON CONFLICT (source_id) DO UPDATE SET
                    sector = EXCLUDED.sector,
                    sub_intent = EXCLUDED.sub_intent,
                    text_content = EXCLUDED.text_content,
                    embedding = EXCLUDED.embedding,
                    lang = EXCLUDED.lang
            """), {
                "sid": source_id,
                "sec": sector,
                "sub": sub_intent,
                "txt": texts[i],
                "emb": vec_str,
                "lang": lang
            })
            
            inserted += 1
            if inserted % 200 == 0:
                print(f"  ... inserted {inserted}/{total}")
                
    print(f"Successfully synced {inserted} records to the PostgreSQL vector store!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--truncate", action="store_true", help="Clear the table before inserting")
    args = parser.parse_args()
    seed_db(args.truncate)
