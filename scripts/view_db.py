import psycopg2
import pandas as pd
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

def main():
    # PostgreSQL bağlantısı (şifre postgres, port 5432)
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/chatbot_db")
    
    print("\n" + "="*50)
    print(" 1) INTENTS TABLOSU (Niyet Kodları)")
    print("="*50)
    df_intents = pd.read_sql("SELECT id, intent_code, url, description FROM intents ORDER BY id;", conn)
    print(df_intents.to_string(index=False))
    
    print("\n" + "="*50)
    print(" 2) SEKTÖR VEKTÖR DAĞILIMI (Vector Index)")
    print("="*50)
    df_sectors = pd.read_sql("SELECT sector, COUNT(*) as record_count FROM vector_index GROUP BY sector ORDER BY record_count DESC;", conn)
    print(df_sectors.to_string(index=False))
    print("="*50 + "\n")
    
    conn.close()

if __name__ == "__main__":
    main()
