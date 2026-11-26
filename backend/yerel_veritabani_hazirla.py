"""Yeni (boş) bir bilgisayarda A'nın tablolarını hazırlar. Sadece yerel test için.

Sorun: Alembic migration'larında `trips`, `trip_members` ve `preferences`
tablolarını oluşturan bir adım yok (A'nın veritabanında elle açılmışlar).
Bu yüzden başka bir bilgisayarda `alembic upgrade head` 2. adımda
("trips" tablosu yok) hata verip HER ŞEYİ geri alıyor. Sonra sunucu açılınca
main.py kullanıcı tablolarını eksik sütunlarla (kvkk_onay vb.) oluşturuyor,
kayıt olurken 500 hatası çıkıyor.

Bu script:
1. Kullanıcı tablolarındaki eksik sütunları ekler (veri silmez).
2. trips / trip_members / preferences tablolarını, migration'ların
   beklediği ilk halleriyle oluşturur (varsa dokunmaz).
3. Kullanıcı tabloları zaten varsa Alembic'e "başlangıç adımı yapıldı" der
   (stamp), böylece `alembic upgrade head` kalan adımları çalıştırabilir.

Kullanım (backend klasöründe):
    python yerel_veritabani_hazirla.py
    python -m alembic upgrade head
"""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASELINE = "e9d415f21c20"

load_dotenv(Path(__file__).resolve().parent / ".env")
url = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    raise SystemExit("backend/.env icinde DATABASE_URL yok.")


def tablo_var(db, ad):
    return db.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{ad}",)).fetchone()[0]


with psycopg.connect(url) as db:
    surum = None
    if tablo_var(db, "alembic_version"):
        satir = db.execute("SELECT version_num FROM alembic_version").fetchone()
        surum = satir[0] if satir else None
    if surum and surum != BASELINE:
        print(f"Alembic zaten '{surum}' surumunde; bu script'e gerek yok.")
        raise SystemExit(0)

    # 1) Kullanici tablolari: main.py'nin eksik actigi sutunlar
    if tablo_var(db, "users"):
        db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kvkk_onay BOOLEAN")
        db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kvkk_onay_tarihi TIMESTAMPTZ")
        db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 0")
        print("users: eksik sutunlar eklendi")
    if tablo_var(db, "pending_signups"):
        db.execute("ALTER TABLE pending_signups ADD COLUMN IF NOT EXISTS kvkk_onay BOOLEAN")
        print("pending_signups: eksik sutun eklendi")
    auth_hazir = tablo_var(db, "users")

    # 2) Migration'larin var saydigi tablolar (696f... adimi bunlara sutun ekler)
    if not auth_hazir:
        print("Kullanici tablolari yok; Alembic olusturacak.")
    db.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id          BIGSERIAL PRIMARY KEY,
            user_id     BIGINT NOT NULL,
            title       VARCHAR(150) NOT NULL,
            destination VARCHAR(150),
            start_date  DATE NOT NULL,
            end_date    DATE NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CHECK (end_date >= start_date)
        )""")
    db.execute("""
        CREATE TABLE IF NOT EXISTS trip_members (
            id        BIGSERIAL PRIMARY KEY,
            trip_id   BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            user_id   BIGINT,
            role      VARCHAR(20) NOT NULL DEFAULT 'member',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (trip_id, user_id)
        )""")
    db.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id         BIGINT PRIMARY KEY,
            nature_score    INTEGER NOT NULL DEFAULT 0,
            food_score      INTEGER NOT NULL DEFAULT 0,
            history_score   INTEGER NOT NULL DEFAULT 0,
            nightlife_score INTEGER NOT NULL DEFAULT 0,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
    print("trips, trip_members, preferences: hazir")

    # 3) Kullanici tablolari zaten varsa baseline'i "yapildi" isaretle
    if auth_hazir and surum is None:
        db.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        db.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (BASELINE,))
        print(f"Alembic baslangic adimi ({BASELINE}) isaretlendi")

print("\nTAMAM. Simdi calistir:  python -m alembic upgrade head")
