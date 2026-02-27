"""Remove unique constraint on guests.tg_chat_id.

Revision ID: 007
Revises: 006
Create Date: 2026-02-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unique constraint on tg_chat_id
    # The index ix_guests_tg_chat_id remains as a non-unique index for query performance
    op.execute(sa.text("DROP INDEX IF EXISTS uq_guests_tg_chat_id"))


def downgrade() -> None:
    # Recreate the unique constraint on tg_chat_id (nullable, but unique when not null)
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_guests_tg_chat_id ON guests (tg_chat_id)
            WHERE tg_chat_id IS NOT NULL
            """
        )
    )
