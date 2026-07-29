import sqlite3

conn = sqlite3.connect('data/qa_embeddings.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM qa_embeddings')
print(f'Total rows: {cursor.fetchone()[0]}')

cursor.execute('SELECT id, question, answer FROM qa_embeddings')
rows = cursor.fetchall()

print('\nAll rows:')
for row in rows:
    print(f'ID: {row[0]}, Q: {row[1][:60]}..., A: {row[2][:60]}...')

conn.close()
