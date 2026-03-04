from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, date, timezone

from app.db.database import get_db
from app.models.appointment import Appointment
from app.models.doctor_availability import DoctorAvailabilitySlot
from app.models.user import User
from app.core.dependencies import require_admin
from app.services.audit_service import log_action

router = APIRouter(tags=["admin-appointments"])


# ==============================
# CREATE APPOINTMENT
# ==============================
@router.post("/appointments")
async def create_appointment(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    # 1️⃣ Check slot exists
    slot_result = await db.execute(
        select(DoctorAvailabilitySlot)
        .where(DoctorAvailabilitySlot.id == data["availability_slot_id"])
    )
    slot = slot_result.scalar_one_or_none()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    # 2️⃣ Check if already booked
    existing = await db.execute(
        select(Appointment).where(
            Appointment.availability_slot_id == slot.id,
            Appointment.status == "scheduled"
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slot already booked")

    # 3️⃣ Create appointment
    appointment = Appointment(
        patient_name=data["patient_name"],
        phone_number=data["phone_number"],
        doctor_id=data["doctor_id"],
        availability_slot_id=slot.id,
        status="scheduled",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    return appointment


# ==============================
# CANCEL APPOINTMENT
# ==============================
@router.delete("/appointments/{appointment_id}")
async def delete_appointment(
    appointment_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )

    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "cancelled"
    appointment.updated_at = datetime.now(timezone.utc)

    await db.commit()

    await log_action(
        db=db,
        user_email=current_user.email,
        action=f"Cancelled Appointment ID {appointment_id}",
        ip_address=request.client.host
    )

    return {"message": "Appointment cancelled successfully"}

# ==============================
# LIST APPOINTMENTS
# ==============================
@router.get("/appointments")
async def list_appointments(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Appointment).order_by(Appointment.created_at.desc())
    )

    return result.scalars().all()