import asyncio
from sqlalchemy import text
from app.db.database import AsyncSessionLocal, engine
from app.db.base import Base

# 🔹 Import ALL models here so tables register
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.token_blacklist import TokenBlacklist
from app.models.doctor import Doctor
from app.models.doctor_schedule import DoctorWeeklySchedule
from app.models.doctor_leave import DoctorLeave
from app.models.session import Session
from app.models.doctor_availability import DoctorAvailabilitySlot
from app.models.appointment import Appointment

from app.core.security import get_password_hash
from app.core.config import settings


async def create_first_admin():
    ADMIN_EMAIL = settings.admin_email
    FULL_NAME = settings.full_name
    ADMIN_PASSWORD = settings.admin_password

    print(f"\n--- 🚀 Starting Fresh Admin Seeding for {ADMIN_EMAIL} ---\n")

    # 🏗️ Recreate All Tables
    async with engine.begin() as conn:
        print("🗑️ Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)

        print("🏗️ Creating fresh database tables...")
        await conn.run_sync(Base.metadata.create_all)

    # 👤 Create Admin User
    async with AsyncSessionLocal() as session:
        try:
            print(f"Adding new admin: {ADMIN_EMAIL}...")

            new_admin = User(
                full_name=FULL_NAME,
                email=ADMIN_EMAIL,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                is_active=True,
                is_superuser=True
            )

            session.add(new_admin)
            await session.commit()

            print("✅ Admin user created successfully!")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error during seeding: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(create_first_admin())