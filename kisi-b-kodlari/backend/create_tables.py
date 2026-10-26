
from database import engine, Base

# Tabloların SQLAlchemy tarafından tanınması için
from models import Destination, Place

print("Tablolar oluşturuluyor...")

Base.metadata.create_all(bind=engine)

print("Tablo oluşturma işlemi tamamlandı!")
