# Kişi B kodları: şehir/yer verisi, rota algoritması, harita

## Klasörler
- `backend/`: FastAPI servisi (port 8001)
  - `main.py`: şehir/yer API'leri ve router'lar
  - `rota_algoritmasi.py`: Haversine, Nearest Neighbor, 2-opt
  - `rota_planlayici.py`: yerleri günlere bölme ve tahmini yol süresi (veritabanı kullanmaz)
  - `rota_servisi.py`: `GET /destinations/{id}/route?days=3&hours_per_day=5`
  - `rota_kayit_servisi.py`: `POST /itineraries`, `GET /itineraries/{id}`
  - `sql/`: tablo ve veri düzeltme SQL'leri
  - `sql_calistir.py`: SQL dosyalarını psql'e gerek kalmadan çalıştırır
  - `tests/`: algoritma testleri
- `frontend-nuxt/`: Nuxt + Leaflet (şehir listesi, harita, rota paneli)

## İlk kurulum / güncellemeden sonra (backend klasöründe)
```
pip install -r requirements.txt
python sql_calistir.py sql/hafta4_itineraries.sql
python sql_calistir.py sql/koordinat_eksik_8_yer.sql
python -m pytest tests -v
uvicorn main:app --reload --port 8001
```
`.env` dosyasında `DATABASE_URL` olmalıdır. Bu dosya repoya eklenmez.

## Rota nasıl hesaplanıyor?
1. Koordinatı ve ziyaret süresi olan yerler alınır.
2. Hepsi NN + 2-opt ile tek bir tura dizilir. Yakın yerler turda art arda gelir.
3. Tur sırayla günlere doldurulur. Her günün süresi şöyle hesaplanır: ziyaret süresi + tahmini yol süresi ≤ günlük saat.
   Süre bolsa yük günlere dengeli dağıtılır.
4. Her günün kendi içindeki sırası yine NN + 2-opt ile iyileştirilir.

Yol süresi tahminidir:
- 1.5 km'ye kadar yürüyüş kabul edilir (kuş uçuşu × 1.3, saatte 4.5 km).
- Daha uzun mesafede toplu taşıma kabul edilir (10 dk bekleme + saatte 18 km).

Gerçek yol tarifi değildir.
