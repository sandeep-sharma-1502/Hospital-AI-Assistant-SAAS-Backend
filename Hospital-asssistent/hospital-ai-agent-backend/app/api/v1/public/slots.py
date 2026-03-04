from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.db.database import get_db
from app.services.appointments.slot_service import SlotService
from app.schemas.slot_schema import SlotResponse

router = APIRouter(
    prefix="/slots",
    tags=["public-slots"]
)

@router.get("/{doctor_id}", response_model=list[SlotResponse])
async def fetch_available_slots(
    doctor_id: int,
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    return await SlotService.get_available_slots(
        db,
        doctor_id,
        target_date
    )