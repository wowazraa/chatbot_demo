import os
import platform

if platform.system() == "Windows":
    # psycopg2 DLL yükleme hatasını önlemek için PostgreSQL bin dizinini DLL arama yoluna ekle
    pg_base = r"C:\Program Files\PostgreSQL"
    if os.path.exists(pg_base):
        for version in os.listdir(pg_base):
            pg_bin = os.path.join(pg_base, version, "bin")
            if os.path.isdir(pg_bin):
                try:
                    os.add_dll_directory(pg_bin)
                except Exception:
                    pass

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    if user and password and host and port and db:
        DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL veya PostgreSQL bağlantı değişkenleri tanımlanmalıdır.")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
