import asyncio
from sqlalchemy import select

from app.db.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings


async def create_first_admin():
    ADMIN_EMAIL = settings.admin_email
    ADMIN_PASSWORD = settings.admin_password

    print(f"\n--- 🚀 Starting Admin Seeding for {ADMIN_EMAIL} ---\n")

    # 1️⃣ Ensure tables exist
    async with engine.begin() as conn:
        print("Checking/Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)

    # 2️⃣ Open session
    async with AsyncSessionLocal() as session:
        try:
            print(f"Checking if {ADMIN_EMAIL} already exists...")

            result = await session.execute(
                select(User).where(User.email == ADMIN_EMAIL)
            )
            existing_user = result.scalars().first()

            if existing_user:
                print(f"ℹ️ User {ADMIN_EMAIL} already exists. Skipping.\n")
                return

            # 3️⃣ Create Admin User
            new_admin = User(
                email=ADMIN_EMAIL,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                is_active=True,
                is_superuser=True  # ✅ Now this exists in model
            )

            session.add(new_admin)
            await session.commit()

            print("✅ Admin user created successfully!")
            print("⚠️ Please change the password after first login.\n")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error during seeding: {str(e)}\n")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(create_first_admin())
    except KeyboardInterrupt:
        print("Seeder interrupted.")