"""Add guest_id and reservation_code to reservations.

Revision ID: 004
Revises: 003
Create Date: 2025-02-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add guest_id as nullable first
    op.add_column(
        "reservations",
        sa.Column("guest_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Backfill: each existing row gets a distinct UUID (not tied to any current guest)
    op.execute(
        sa.text(
            "UPDATE reservations SET guest_id = gen_random_uuid() WHERE guest_id IS NULL"
        )
    )
    op.alter_column(
        "reservations",
        "guest_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_index(
        op.f("ix_reservations_guest_id"), "reservations", ["guest_id"], unique=False
    )

    # Add reservation_code as nullable
    op.add_column(
        "reservations",
        sa.Column("reservation_code", sa.String(length=8), nullable=True),
    )
    # Backfill: deterministic 8-char code per row from id so unique
    op.execute(
        sa.text(
            "UPDATE reservations SET reservation_code = lower(substring(md5(id::text) from 1 for 8)) WHERE reservation_code IS NULL"
        )
    )
    op.create_index(
        op.f("ix_reservations_reservation_code"),
        "reservations",
        ["reservation_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_reservations_reservation_code"), table_name="reservations"
    )
    op.drop_column("reservations", "reservation_code")
    op.drop_index(op.f("ix_reservations_guest_id"), table_name="reservations")
    op.drop_column("reservations", "guest_id")
