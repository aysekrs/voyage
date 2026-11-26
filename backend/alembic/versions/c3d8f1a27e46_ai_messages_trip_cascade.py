"""ai_messages: seyahat silinince o seyahatin sohbet mesajları da silinsin

Revision ID: c3d8f1a27e46
Revises: b7e2a4c91d05
Create Date: 2026-11-26

Önceki ayarda (ON DELETE SET NULL) seyahat silinince mesajların trip_id'si
boşalıyordu. Boş trip_id "henüz onaylanmamış açık sohbet" anlamına geldiği için
silinen seyahatin sohbeti asistanda yeniden açık sohbet gibi görünüyordu.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3d8f1a27e46"
down_revision: Union[str, Sequence[str], None] = "b7e2a4c91d05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK = "ai_messages_trip_id_fkey"  # PostgreSQL'in otomatik verdiği ad


def upgrade() -> None:
    op.drop_constraint(FK, "ai_messages", type_="foreignkey")
    op.create_foreign_key(FK, "ai_messages", "trips", ["trip_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint(FK, "ai_messages", type_="foreignkey")
    op.create_foreign_key(FK, "ai_messages", "trips", ["trip_id"], ["id"], ondelete="SET NULL")
