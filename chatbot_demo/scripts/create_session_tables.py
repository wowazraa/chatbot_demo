import sys
import os
from pathlib import Path

# Script dizininden chatbot_demo klasörüne ulaşım
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.schema import DDL_STATEMENTS
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def create_session_tables():
    """Session ve messages tablolarını oluştur"""
    
    db_url = os.getenv('DATABASE_URL').replace('postgresql+psycopg2://', 'postgresql://')
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("[1] Session tablolarını oluşturuyor...")
        
        # DDL_STATEMENTS'ın içinde session tabloları var
        # Sadece session tablolarını çalıştırmak için filtreleyelim
        session_ddls = [stmt for stmt in DDL_STATEMENTS if 'chat_sessions' in stmt or 'chat_messages' in stmt]
        
        for ddl in session_ddls:
            try:
                cursor.execute(ddl)
                conn.commit()
                print(f"[OK] Tablo/İndeks oluşturuldu")
            except psycopg2.errors.DuplicateTable:
                conn.rollback()
                print(f"[INFO] Tablo zaten mevcut, atlanıyor")
            except psycopg2.errors.DuplicateObject:
                conn.rollback()
                print(f"[INFO] İndeks zaten mevcut, atlanıyor")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] DDL hatası: {e}")
                raise
        
        print("[2] Tablolar doğrulanıyor...")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('chat_sessions', 'chat_messages')")
        tables = cursor.fetchall()
        
        print(f"[OK] Oluşturulan tablolar: {[t[0] for t in tables]}")
        
        if len(tables) == 2:
            print("[SUCCESS] Session tabloları başarıyla oluşturuldu!")
        else:
            print(f"[WARNING] Beklenen 2 tablo, {len(tables)} tablo bulundu")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Session tabloları oluşturulurken hata: {e}")
        raise e

if __name__ == "__main__":
    create_session_tables()
