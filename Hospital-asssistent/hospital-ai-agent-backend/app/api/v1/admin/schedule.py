from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.doctor_schedule import DoctorWeeklySchedule
from pydantic import BaseModel
from datetime import time

router = APIRouter(prefix="/doctors", tags=["admin-schedule"])

class WeeklyScheduleCreate(BaseModel):
    weekday: int
    start_time: time
    end_time: time


@router.post("/{doctor_id}/schedule")
async def create_schedule(
    doctor_id: int,
    data: WeeklyScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    schedule = DoctorWeeklySchedule(
        doctor_id=doctor_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time
    )

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return schedule