
"""week3_trip_preferences

Revision ID: d550b3094bf9
Revises: 696f5f5a7dec
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d550b3094bf9"
down_revision: Union[str, Sequence[str], None] = "696f5f5a7dec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trip_preferences",

        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True
        ),

        sa.Column(
            "trip_id",
            sa.BigInteger(),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
            unique=True
        ),

        sa.Column(
            "nature_weight",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "food_weight",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "history_weight",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "nightlife_weight",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.CheckConstraint(
            """
            nature_weight >= 0 AND
            food_weight >= 0 AND
            history_weight >= 0 AND
            nightlife_weight >= 0
            """,
            name="trip_preferences_nonnegative"
        ),

        sa.CheckConstraint(
            """
            nature_weight + food_weight +
            history_weight + nightlife_weight = 100
            """,
            name="trip_preferences_total_100"
        )
    )


def downgrade() -> None:
    op.drop_table("trip_preferences")
