"""Sektör isimlerini düzelt + 4 sektörü garanti et."""
import psycopg2

ROWS = [
    ("health", "Sağlık", "Health"),
    ("tourism", "Turizm", "Tourism"),
    ("education", "Eğitim", "Education"),
    ("bilisim", "Bilişim", "IT"),
    ("eglence", "Eğlence", "Entertainment"),
]

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/chatbot_db")
conn.autocommit = True
cur = conn.cursor()
for key, tr, en in ROWS:
    cur.execute(
        """
        INSERT INTO sectors (sector_key, sector_name_tr, sector_name_en)
        VALUES (%s, %s, %s)
        ON CONFLICT (sector_key) DO UPDATE
        SET sector_name_tr = EXCLUDED.sector_name_tr,
            sector_name_en = EXCLUDED.sector_name_en
        """,
        (key, tr, en),
    )
cur.execute("SELECT id, sector_key, sector_name_tr FROM sectors ORDER BY id")
for row in cur.fetchall():
    print(row[0], row[1], row[2])
cur.close()
conn.close()
print("OK")
