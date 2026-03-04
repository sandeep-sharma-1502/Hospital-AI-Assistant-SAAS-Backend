from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from datetime import datetime, timedelta, date

from app.db.database import get_db
from app.models.doctor_schedule import DoctorWeeklySchedule
from app.models.doctor_leave import DoctorLeave
from app.models.doctor_availability import DoctorAvailabilitySlot

router = APIRouter(prefix="/doctors", tags=["admin-slots"])


@router.post("/{doctor_id}/generate-slots")
async def generate_slots(
    doctor_id: int,
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate availability slots for a doctor on a specific date.
    """

    # 1️⃣ Check if doctor has schedule for that weekday
    weekday = target_date.weekday()

    schedule_result = await db.execute(
        select(DoctorWeeklySchedule).where(
            DoctorWeeklySchedule.doctor_id == doctor_id,
            DoctorWeeklySchedule.weekday == weekday,
            DoctorWeeklySchedule.is_active == True
        )
    )

    schedule = schedule_result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=400,
            detail="Doctor has no working schedule for this day"
        )

    # 2️⃣ Check if doctor is on leave
    leave_result = await db.execute(
        select(DoctorLeave).where(
            DoctorLeave.doctor_id == doctor_id,
            DoctorLeave.leave_date == target_date
        )
    )

    leave = leave_result.scalar_one_or_none()

    if leave:
        raise HTTPException(
            status_code=400,
            detail="Doctor is on leave on this date"
        )

    # 3️⃣ Delete existing slots for that date (prevent duplicates)
    await db.execute(
        delete(DoctorAvailabilitySlot).where(
            DoctorAvailabilitySlot.doctor_id == doctor_id,
            DoctorAvailabilitySlot.start_time >= datetime.combine(target_date, schedule.start_time),
            DoctorAvailabilitySlot.start_time < datetime.combine(target_date + timedelta(days=1), schedule.start_time)
        )
    )

    # 4️⃣ Generate time intervals (30 minutes)
    slot_duration = timedelta(minutes=30)

    start_datetime = datetime.combine(target_date, schedule.start_time)
    end_datetime = datetime.combine(target_date, schedule.end_time)

    slots_created = []

    current_time = start_datetime

    while current_time + slot_duration <= end_datetime:
        new_slot = DoctorAvailabilitySlot(
            doctor_id=doctor_id,
            start_time=current_time,
            end_time=current_time + slot_duration
        )

        db.add(new_slot)
        slots_created.append(new_slot)

        current_time += slot_duration

    await db.commit()

    return {
        "message": "Slots generated successfully",
        "total_slots": len(slots_created),
        "date": target_date
    }