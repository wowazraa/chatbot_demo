import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_db')

# Parse connection string
if 'postgresql+psycopg2://' in DB_URL:
    DB_URL = DB_URL.replace('postgresql+psycopg2://', 'postgresql://')

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM qa_embeddings')
    print(f'Total rows: {cursor.fetchone()[0]}')
    
    # Check the deleted rows' sector labels to see if they were legitimate OOD training data
    cursor.execute('SELECT id, question, answer FROM qa_embeddings WHERE question IN (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', ('günaydın nasılsınız', 'orada kimse var mı', 'ne iş yapıyorsunuz', 'who is the founder of this platform', 'nasılsın', 'nasılsınız', 'naber', 'ne haber', 'nehaber nasılsın', 'how are you', 'how are you doing', 'how is it going', 'hows it going', 'whats up', 'nehaber'))
    rows = cursor.fetchall()
    
    print(f'\nDeleted rows check (should be 0 if already deleted): {len(rows)}')
    if len(rows) > 0:
        print('Rows still exist - checking their sector labels:')
        for row in rows:
            print(f'ID: {row[0]}, Q: "{row[1]}", A: "{row[2][:50]}..."')
    else:
        print('Rows were already deleted. Need to restore them if they were legitimate OOD training data.')
    
    conn.close()
except Exception as e:
    print(f'Error: {e}')
