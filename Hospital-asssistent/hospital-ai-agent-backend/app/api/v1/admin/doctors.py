from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.doctor import Doctor
from app.schemas.doctor_schema import DoctorCreate, DoctorResponse
from app.services.doctor_service import DoctorService

router = APIRouter(prefix="/doctors", tags=["admin-doctors"])

@router.post("/", response_model=DoctorResponse)
async def create_doctor(
    data: DoctorCreate,
    db: AsyncSession = Depends(get_db)
):
    return await DoctorService.create_doctor(db, data)


# ================================
# LIST DOCTORS  🔥 ADD THIS
# ================================
@router.get("/", response_model=list[DoctorResponse])
async def list_doctors(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Doctor))
    return result.scalars().all()