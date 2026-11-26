
"""week3_trips_fields

Revision ID: 696f5f5a7dec
Revises: e9d415f21c20
Create Date: 2026-11-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "696f5f5a7dec"
down_revision: Union[str, Sequence[str], None] = "e9d415f21c20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("origin_city", sa.String(150), nullable=True)
    )

    op.add_column(
        "trips",
        sa.Column("origin_airport_code", sa.String(10), nullable=True)
    )

    op.add_column(
        "trips",
        sa.Column("budget_try", sa.Numeric(12, 2), nullable=True)
    )

    op.add_column(
        "trips",
        sa.Column("people_count", sa.Integer(), nullable=True)
    )

    op.add_column(
        "trips",
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="planning"
        )
    )

    op.add_column(
        "trips",
        sa.Column("selected_destination_id", sa.BigInteger(), nullable=True)
    )

    op.add_column(
        "trips",
        sa.Column("user_text", sa.Text(), nullable=True)
    )

    op.create_check_constraint(
        "trips_budget_positive",
        "trips",
        "budget_try IS NULL OR budget_try > 0"
    )

    op.create_check_constraint(
        "trips_people_count_positive",
        "trips",
        "people_count IS NULL OR people_count > 0"
    )


def downgrade() -> None:
    op.drop_constraint(
        "trips_people_count_positive", "trips", type_="check"
    )
    op.drop_constraint(
        "trips_budget_positive", "trips", type_="check"
    )

    op.drop_column("trips", "user_text")
    op.drop_column("trips", "selected_destination_id")
    op.drop_column("trips", "status")
    op.drop_column("trips", "people_count")
    op.drop_column("trips", "budget_try")
    op.drop_column("trips", "origin_airport_code")
    op.drop_column("trips", "origin_city")
