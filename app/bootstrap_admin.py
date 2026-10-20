import asyncio
from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.entities import Base, User

async def main():
    email, password = settings.bootstrap_admin_email.strip().lower(), settings.bootstrap_admin_password
    if not email or not password: raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in .env")
    if len(password) < 12: raise SystemExit("Bootstrap password must be at least 12 characters")
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        if await db.scalar(select(User).where(User.email == email)): print(f"User already exists: {email}"); return
        db.add(User(email=email, full_name="Agency Administrator", password_hash=hash_password(password))); await db.commit()
        print(f"Created {email}; ensure AGENCY_ADMIN_EMAILS contains this address.")
    await engine.dispose()

if __name__ == "__main__": asyncio.run(main())
