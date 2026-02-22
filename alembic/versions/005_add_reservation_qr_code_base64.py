"""Add qr_code_base64 to reservations.

Revision ID: 005
Revises: 004
Create Date: 2025-02-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column("qr_code_base64", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reservations", "qr_code_base64")
