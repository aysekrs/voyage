"""airports: dünyadaki tarifeli havalimanları (kalkış şehri seçimi için)

Revision ID: d4a9e2b6c813
Revises: c3d8f1a27e46
Create Date: 2026-11-26

Veri backend/veri/havalimanlari.csv dosyasından yüklenir (OurAirports, kamu malı).
Veriyi güncellemek için: veri/havalimanlari_hazirla.py ile CSV'yi yeniden üretip
bu tabloyu boşaltıp tekrar yükleyin (ya da downgrade + upgrade).
"""
import csv
import sys
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4a9e2b6c813"
down_revision: Union[str, Sequence[str], None] = "c3d8f1a27e46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BACKEND = Path(__file__).resolve().parents[2]
CSV_YOLU = BACKEND / "veri" / "havalimanlari.csv"


def upgrade() -> None:
    sys.path.insert(0, str(BACKEND))
    from havalimani_arama import arama_metni, normalize

    tablo = op.create_table(
        "airports",
        sa.Column("iata", sa.String(3), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("city_tr", sa.Text(), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("country_tr", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        # Türkçe karakter/aksan duyarsız arama metni (havalimani_arama.normalize)
        sa.Column("arama", sa.Text(), nullable=False),
        # Sadece şehir adları (Türkçe + yerel): şehirle başlayan sonuçlar öne çıkar
        sa.Column("sehir_arama", sa.Text(), nullable=False),
    )

    satirlar = []
    with CSV_YOLU.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            satirlar.append({
                "iata": r["iata"],
                "name": r["name"],
                "city": r["city"],
                "city_tr": r["city_tr"] or None,
                "country_code": r["country_code"],
                "country": r["country"],
                "country_tr": r["country_tr"] or None,
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "type": r["type"],
                "arama": arama_metni(r),
                "sehir_arama": " " + normalize(f"{r['city_tr']} {r['city']}") + " ",
            })
    op.bulk_insert(tablo, satirlar)


def downgrade() -> None:
    op.drop_table("airports")
