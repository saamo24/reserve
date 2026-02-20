"""Initial schema: branches, tables, reservations.

Revision ID: 001
Revises:
Create Date: 2025-02-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("opening_time", sa.Time(), nullable=False),
        sa.Column("closing_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_branches_name"), "branches", ["name"], unique=False)

    op.create_table(
        "tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("table_number", sa.String(length=32), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("location", sa.Enum("INDOOR", "OUTDOOR", "VIP", name="tablelocation"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id", "table_number", name="uq_tables_branch_table_number"),
    )
    op.create_index(op.f("ix_tables_branch_capacity"), "tables", ["branch_id", "capacity"], unique=False)
    op.create_index(op.f("ix_tables_branch_id"), "tables", ["branch_id"], unique=False)

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("reservation_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "CANCELLED", "COMPLETED", name="reservationstatus"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reservations_branch_date"), "reservations", ["branch_id", "reservation_date"], unique=False)
    op.create_index(op.f("ix_reservations_branch_id"), "reservations", ["branch_id"], unique=False)
    op.create_index(op.f("ix_reservations_phone_number"), "reservations", ["phone_number"], unique=False)
    op.create_index(op.f("ix_reservations_reservation_date"), "reservations", ["reservation_date"], unique=False)
    op.create_index(op.f("ix_reservations_table_date"), "reservations", ["table_id", "reservation_date"], unique=False)
    op.create_index(
        op.f("ix_reservations_table_date_times"),
        "reservations",
        ["table_id", "reservation_date", "start_time", "end_time"],
        unique=False,
    )
    op.create_index(op.f("ix_reservations_table_id"), "reservations", ["table_id"], unique=False)

    # Partial unique index: prevent duplicate active reservation for same slot
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_reservations_table_slot_active ON reservations "
            "(table_id, reservation_date, start_time, end_time) "
            "WHERE status NOT IN ('CANCELLED')"
        )
    )


def downgrade() -> None:
    op.drop_index("uq_reservations_table_slot_active", table_name="reservations")
    op.drop_index(op.f("ix_reservations_table_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_table_date_times"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_table_date"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_reservation_date"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_phone_number"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_branch_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_branch_date"), table_name="reservations")
    op.drop_table("reservations")
    op.drop_index(op.f("ix_tables_branch_id"), table_name="tables")
    op.drop_index(op.f("ix_tables_branch_capacity"), table_name="tables")
    op.drop_table("tables")
    op.drop_index(op.f("ix_branches_name"), table_name="branches")
    op.drop_table("branches")
    op.execute(sa.text("DROP TYPE reservationstatus"))
    op.execute(sa.text("DROP TYPE tablelocation"))
