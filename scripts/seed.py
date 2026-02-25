#!/usr/bin/env python3
"""Seed branches, tables, and default admin (idempotent). Run after migrations."""

import asyncio
import sys
from datetime import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.branch import Branch
from app.models.table import Table, TableLocation


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Idempotent: create default admin if missing
        admin_result = await session.execute(select(Admin).where(Admin.email == settings.admin_email))
        if admin_result.scalar_one_or_none() is None:
            admin = Admin(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_temp_password),
            )
            session.add(admin)
            await session.flush()
            print(f"Created default admin user (email: {settings.admin_email}, password: {settings.admin_temp_password}). Change in production.")

        # Idempotent: skip if branch already exists
        result = await session.execute(select(Branch).where(Branch.name == "Main Branch"))
        existing = result.scalar_one_or_none()
        if existing:
            print("Branch 'Main Branch' already exists, skipping seed.")
            await session.commit()
            return

        branch = Branch(
            name="Main Branch",
            address="123 Restaurant St, City",
            opening_time=time(11, 0),
            closing_time=time(23, 0),
            slot_duration_minutes=120,
            is_active=True,
        )
        session.add(branch)
        await session.flush()

        for i in range(1, 6):
            table = Table(
                branch_id=branch.id,
                table_number=str(i),
                capacity=4,
                location=TableLocation.INDOOR if i <= 3 else TableLocation.OUTDOOR,
                is_active=True,
            )
            session.add(table)

        await session.commit()
        print(f"Created branch {branch.id} and 5 tables.")


if __name__ == "__main__":
    asyncio.run(main())
