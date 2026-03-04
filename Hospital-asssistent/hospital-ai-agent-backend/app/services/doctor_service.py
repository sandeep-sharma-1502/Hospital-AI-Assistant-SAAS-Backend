from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.doctor import Doctor
from app.schemas.doctor_schema import DoctorCreate


class DoctorService:

    @staticmethod
    async def create_doctor(db: AsyncSession, data: DoctorCreate):

        # 🔍 Check duplicate doctor (same name + department)
        existing_query = await db.execute(
            select(Doctor).where(
                Doctor.name == data.name,
                Doctor.department == data.department
            )
        )

        existing_doctor = existing_query.scalar_one_or_none()

        if existing_doctor:
            raise ValueError("Doctor already exists in this department.")

        try:
            doctor = Doctor(
                name=data.name,
                department=data.department,
                specialization=data.specialization
            )

            db.add(doctor)
            await db.commit()
            await db.refresh(doctor)

            return doctor

        except Exception as e:
            await db.rollback()
            raise e