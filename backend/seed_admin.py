"""Create the first admin account.

Usage:
    python seed_admin.py "Admin Name" admin@example.com "a-strong-password"
"""
import asyncio
import sys
from sqlalchemy import select
from utils.db import AsyncSessionLocal, init_db
from models import User
from utils.auth import hash_password


async def seed(name: str, email: str, password: str):
    await init_db()
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none():
            print(f"A user with {email} already exists — nothing to do.")
            return
        db.add(User(
            role="admin",
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            is_approved=True,
            is_active=True,
        ))
        await db.commit()
        print(f"Admin created: {email}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    asyncio.run(seed(sys.argv[1], sys.argv[2], sys.argv[3]))
