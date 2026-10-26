
from database import engine, Base
from city_models import Sehir, Yer

print("Yeni VoyageAI tablolari olusturuluyor...")

Base.metadata.create_all(bind=engine)

print("Sehirler ve yerler tablolarinin kurulumu tamamlandi!")
