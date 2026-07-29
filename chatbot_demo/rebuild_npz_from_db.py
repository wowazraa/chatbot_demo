import os
import psycopg2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_db')

# Parse connection string
if 'postgresql+psycopg2://' in DB_URL:
    DB_URL = DB_URL.replace('postgresql+psycopg2://', 'postgresql://')

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Fetch all data from qa_embeddings
    cursor.execute('SELECT id, question, answer, embedding FROM qa_embeddings ORDER BY id')
    rows = cursor.fetchall()
    
    print(f'Fetched {len(rows)} rows from database')
    
    # Prepare data for NPZ
    ids = []
    questions = []
    answers = []
    embeddings = []
    
    for row in rows:
        ids.append(row[0])
        questions.append(row[1])
        answers.append(row[2])
        embeddings.append(np.array(row[3], dtype=np.float32))
    
    embeddings_array = np.array(embeddings, dtype=np.float32)
    
    # Save to NPZ
    np.savez(
        'data/embeddings.npz',
        ids=np.array(ids),
        questions=np.array(questions, dtype=object),
        answers=np.array(answers, dtype=object),
        embeddings=embeddings_array
    )
    
    print(f'Saved {len(ids)} rows to data/embeddings.npz')
    print(f'Embeddings shape: {embeddings_array.shape}')
    
    conn.close()
except Exception as e:
    print(f'Error: {e}')
