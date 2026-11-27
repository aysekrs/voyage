-- VoyageAI - Hafta 4: kaydedilen rota tabloları (itineraries, itinerary_stops)
--
-- Çalıştırma:  python sql_calistir.py sql/hafta4_itineraries.sql
--
-- Tablolar zaten varsa (elle açıldıysa) bozulmaz: CREATE ... IF NOT EXISTS
-- ve ADD COLUMN IF NOT EXISTS kullanılır, mevcut kayıtlar silinmez.
-- Tekrar tekrar çalıştırmak güvenlidir.
--
-- Not: Ekip şemasındaki trip_id (FK -> trips) ve version alanları burada
-- boş bırakılabilir şekilde eklendi. 6. haftada rota seyahate bağlanınca
-- (/trips/{id}/itinerary) trip_id doldurulacak. trips tablosu A'nın
-- Alembic migration'larıyla açıldığı için FK'yı o zaman A ile birlikte ekleyin.

CREATE TABLE IF NOT EXISTS itineraries (
    itinerary_id        SERIAL PRIMARY KEY,
    sehir_id            INTEGER NOT NULL REFERENCES sehirler(sehir_id),
    gun_sayisi          INTEGER NOT NULL CHECK (gun_sayisi BETWEEN 1 AND 7),
    gunluk_saat         INTEGER NOT NULL CHECK (gunluk_saat BETWEEN 1 AND 12),
    toplam_mesafe_km    DOUBLE PRECISION NOT NULL DEFAULT 0,
    olusturulma_tarihi  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Ekip şemasından gelen alanlar (eski tabloya da eklenir)
ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS trip_id             BIGINT;
ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS version             INTEGER NOT NULL DEFAULT 1;
ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS algorithm           VARCHAR(80);
ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS user_request_filter TEXT;
ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS toplam_yol_dk       INTEGER;

CREATE TABLE IF NOT EXISTS itinerary_stops (
    id                  SERIAL PRIMARY KEY,
    itinerary_id        INTEGER NOT NULL REFERENCES itineraries(itinerary_id) ON DELETE CASCADE,
    yer_id              INTEGER NOT NULL REFERENCES yerler(yer_id),
    gun_no              INTEGER NOT NULL CHECK (gun_no >= 1),
    sira                INTEGER NOT NULL CHECK (sira >= 1),
    ziyaret_suresi      INTEGER NOT NULL,
    onceki_duraktan_km  DOUBLE PRECISION NOT NULL DEFAULT 0,
    UNIQUE (itinerary_id, gun_no, sira)
);

ALTER TABLE itinerary_stops ADD COLUMN IF NOT EXISTS yol_suresi_dk INTEGER;

CREATE INDEX IF NOT EXISTS ix_itinerary_stops_itinerary ON itinerary_stops(itinerary_id);
CREATE INDEX IF NOT EXISTS ix_itineraries_sehir ON itineraries(sehir_id);

-- Kontrol: iki tablonun sütunları
SELECT table_name, column_name, data_type
  FROM information_schema.columns
 WHERE table_name IN ('itineraries', 'itinerary_stops')
 ORDER BY table_name, ordinal_position;
