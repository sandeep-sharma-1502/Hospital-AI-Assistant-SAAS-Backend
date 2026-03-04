
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models.appointment import Appointment
from app.models.doctor_availability import DoctorAvailabilitySlot


class AppointmentService:

    # =========================================================
    # CREATE APPOINTMENT (BOT + ADMIN SAFE)
    # =========================================================
    @staticmethod
    async def create_appointment(db: AsyncSession, data):

        result = await db.execute(
            select(DoctorAvailabilitySlot)
            .where(DoctorAvailabilitySlot.id == data.availability_slot_id)
            .with_for_update()
        )

        slot = result.scalar_one_or_none()

        if not slot:
            raise ValueError("Slot not found")

        if slot.is_booked:
            raise ValueError("Slot already booked")

        if data.doctor_id != slot.doctor_id:
            raise ValueError("Doctor mismatch for selected slot")

        if slot.start_time < datetime.utcnow():
            raise ValueError("Cannot book past slot")

        appointment = Appointment(
            patient_name=data.patient_name,
            phone_number=data.phone_number,
            doctor_id=slot.doctor_id,
            availability_slot_id=slot.id,
            status="scheduled",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        slot.is_booked = True
        db.add(appointment)

        return appointment


    # =========================================================
    # ✅ ATOMIC BOOKING (BOT CONFIRMATION SAFE)
    # =========================================================
    @staticmethod
    async def create_atomic_booking(
        db: AsyncSession,
        slot_id: int,
        doctor_id: int,
        patient_name: str,
        phone_number: str,
    ):

        # 🔒 Lock slot row
        result = await db.execute(
            select(DoctorAvailabilitySlot)
            .where(DoctorAvailabilitySlot.id == slot_id)
            .with_for_update()
        )

        slot = result.scalar_one_or_none()

        if not slot:
            raise ValueError("Slot not found")

        if slot.is_booked:
            raise ValueError("Slot already booked")

        if slot.doctor_id != doctor_id:
            raise ValueError("Doctor mismatch")

        if slot.start_time < datetime.utcnow():
            raise ValueError("Cannot book past slot")

        # Create appointment
        appointment = Appointment(
            patient_name=patient_name,
            phone_number=phone_number,
            doctor_id=slot.doctor_id,
            availability_slot_id=slot.id,
            status="scheduled",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Mark slot booked
        slot.is_booked = True

        db.add(appointment)

        await db.flush()  # ensures appointment.id available

        return appointment


    # =========================================================
    # CANCEL APPOINTMENT
    # =========================================================
    @staticmethod
    async def cancel_appointment(db: AsyncSession, appointment_id: int):

        result = await db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )

        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError("Appointment not found")

        if appointment.status == "cancelled":
            raise ValueError("Appointment already cancelled")

        slot_result = await db.execute(
            select(DoctorAvailabilitySlot)
            .where(DoctorAvailabilitySlot.id == appointment.availability_slot_id)
            .with_for_update()
        )

        slot = slot_result.scalar_one_or_none()

        if slot:
            slot.is_booked = False

        appointment.status = "cancelled"
        appointment.updated_at = datetime.utcnow()

        return appointment


    # =========================================================
    # RESCHEDULE APPOINTMENT
    # =========================================================
    @staticmethod
    async def reschedule_appointment(
        db: AsyncSession,
        appointment_id: int,
        new_slot_id: int
    ):

        result = await db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )

        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError("Appointment not found")

        if appointment.status == "cancelled":
            raise ValueError("Cannot reschedule cancelled appointment")

        if appointment.availability_slot_id == new_slot_id:
            raise ValueError("Already booked on this slot")

        new_slot_result = await db.execute(
            select(DoctorAvailabilitySlot)
            .where(DoctorAvailabilitySlot.id == new_slot_id)
            .with_for_update()
        )

        new_slot = new_slot_result.scalar_one_or_none()

        if not new_slot:
            raise ValueError("New slot not found")

        if new_slot.is_booked:
            raise ValueError("New slot already booked")

        old_slot_result = await db.execute(
            select(DoctorAvailabilitySlot)
            .where(DoctorAvailabilitySlot.id == appointment.availability_slot_id)
            .with_for_update()
        )

        old_slot = old_slot_result.scalar_one_or_none()

        if old_slot:
            old_slot.is_booked = False

        new_slot.is_booked = True

        appointment.availability_slot_id = new_slot.id
        appointment.doctor_id = new_slot.doctor_id
        appointment.updated_at = datetime.utcnow()

        return appointment


    # =========================================================
    # LIST APPOINTMENTS
    # =========================================================
    @staticmethod
    async def list_appointments(db: AsyncSession):

        result = await db.execute(
            select(Appointment)
            .order_by(Appointment.created_at.desc())
        )

        return result.scalars().all()