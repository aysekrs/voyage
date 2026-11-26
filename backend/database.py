
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# .env dosyasındaki bilgileri oku
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL bulunamadi!")

# PostgreSQL bağlantısını hazırla
engine = create_engine(DATABASE_URL)

# Veritabanı oturumlarını oluştur
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False
)

# Tablolarımız için temel sınıf
class Base(DeclarativeBase):
    pass

# Bağlantıyı test et
if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database()")
            )

            print("Veritabani baglantisi basarili!")
            print("Baglanilan veritabani:", result.scalar())

    except Exception as error:
        print("Veritabani baglantisi basarisiz!")
        print(error)
