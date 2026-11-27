"""yerler: B'nin veri alanları (fiyat para birimi vb.)

B'nin veritabanında yerler tablosunda bu sütunlar var; A'nın veritabanında
yoktu. Öneri hesabı ücretin para birimini okuduğu için her veritabanında
bulunmaları gerekiyor. Sütun zaten varsa dokunulmaz.

Revision ID: e5b1c7a9d2f4
Revises: d4a9e2b6c813
Create Date: 2026-11-27

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5b1c7a9d2f4"
down_revision: Union[str, Sequence[str], None] = "d4a9e2b6c813"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SUTUNLAR = {
    "veri_durumu": "text",
    "kaynak_aday_id": "bigint",
    "resmi_kaynak": "text",
    "fiyat_para_birimi": "text",
    "fiyat_turu": "text",
    "fiyat_kontrol_tarihi": "date",
    "ziyaret_suresi_turu": "text",
}


def upgrade() -> None:
    for ad, tip in SUTUNLAR.items():
        op.execute(f"ALTER TABLE yerler ADD COLUMN IF NOT EXISTS {ad} {tip}")


def downgrade() -> None:
    # B'nin veritabanında bu sütunlar asıl veridir; geri alırken silinmez.
    pass
