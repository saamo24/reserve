"""Add guests table and update reservations foreign key.

Revision ID: 006
Revises: 005
Create Date: 2025-02-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create guests table
    op.create_table(
        "guests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tg_chat_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guests_tg_chat_id", "guests", ["tg_chat_id"], unique=False)
    # Create unique constraint on tg_chat_id (nullable, but unique when not null)
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_guests_tg_chat_id ON guests (tg_chat_id)
            WHERE tg_chat_id IS NOT NULL
            """
        )
    )

    # Migrate existing guest_id values: create Guest records for unique guest_ids
    op.execute(
        sa.text(
            """
            INSERT INTO guests (id, created_at, updated_at)
            SELECT DISTINCT guest_id, MIN(created_at), MIN(created_at)
            FROM reservations
            WHERE guest_id IS NOT NULL
            GROUP BY guest_id
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    # Add foreign key constraint from reservations.guest_id to guests.id
    op.create_foreign_key(
        "fk_reservations_guest_id_guests",
        "reservations",
        "guests",
        ["guest_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint("fk_reservations_guest_id_guests", "reservations", type_="foreignkey")
    
    # Drop guests table
    op.drop_index("ix_guests_tg_chat_id", table_name="guests")
    op.execute(sa.text("DROP INDEX IF EXISTS uq_guests_tg_chat_id"))
    op.drop_table("guests")
