import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
db_url = os.getenv('DATABASE_URL').replace('postgresql+psycopg2://', 'postgresql://')

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM intents')
intent_count = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM qa_embeddings')
qa_count = cur.fetchone()[0]

cur.execute('SELECT i.intent_code, COUNT(qe.id) FROM intents i LEFT JOIN qa_embeddings qe ON i.id = qe.intent_id GROUP BY i.intent_code')
intent_distribution = cur.fetchall()

print(f'DB Intent sayısı: {intent_count}')
print(f'DB QA sayısı: {qa_count}')
print('Intent dağılımı:')
for code, count in intent_distribution:
    print(f'  {code}: {count}')

cur.close()
conn.close()
