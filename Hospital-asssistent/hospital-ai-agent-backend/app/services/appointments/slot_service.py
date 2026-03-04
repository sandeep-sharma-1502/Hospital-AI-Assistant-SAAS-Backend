from datetime import datetime, timedelta, date
from typing import List, Tuple, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.doctor import Doctor
from app.models.doctor_schedule import DoctorWeeklySchedule
from app.models.doctor_leave import DoctorLeave
from app.models.doctor_availability import DoctorAvailabilitySlot


class SlotService:

    SLOT_DURATION_MINUTES = 15

    # =========================================================
    # GENERATE SLOTS FOR SINGLE DAY
    # =========================================================
    @staticmethod
    async def generate_slots_for_day(
        db: AsyncSession,
        doctor_id: int,
        target_date: date
    ) -> List[DoctorAvailabilitySlot]:

        # 1️⃣ Validate doctor
        doctor_query = await db.execute(
            select(Doctor).where(
                Doctor.id == doctor_id,
                Doctor.is_active == True
            )
        )
        doctor = doctor_query.scalar_one_or_none()

        if not doctor:
            raise ValueError("Doctor not found or inactive.")

        weekday = target_date.weekday()

        # 2️⃣ Get weekly schedule
        schedule_query = await db.execute(
            select(DoctorWeeklySchedule).where(
                DoctorWeeklySchedule.doctor_id == doctor_id,
                DoctorWeeklySchedule.weekday == weekday,
                DoctorWeeklySchedule.is_active == True
            )
        )
        schedules = schedule_query.scalars().all()

        if not schedules:
            return []

        # 3️⃣ Check leave
        leave_query = await db.execute(
            select(DoctorLeave).where(
                DoctorLeave.doctor_id == doctor_id,
                DoctorLeave.leave_date == target_date
            )
        )
        leave = leave_query.scalar_one_or_none()

        if leave:
            return []

        # 4️⃣ Fetch existing slots
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        existing_query = await db.execute(
            select(DoctorAvailabilitySlot).where(
                DoctorAvailabilitySlot.doctor_id == doctor_id,
                DoctorAvailabilitySlot.start_time >= day_start,
                DoctorAvailabilitySlot.start_time < day_end
            )
        )

        existing_slots = {
            slot.start_time: slot
            for slot in existing_query.scalars().all()
        }

        created_slots = []

        # 5️⃣ Generate missing slots
        for schedule in schedules:

            start_dt = datetime.combine(target_date, schedule.start_time)
            end_dt = datetime.combine(target_date, schedule.end_time)

            current = start_dt

            while current < end_dt:

                slot_end = current + timedelta(
                    minutes=SlotService.SLOT_DURATION_MINUTES
                )

                if current not in existing_slots:
                    slot = DoctorAvailabilitySlot(
                        doctor_id=doctor_id,
                        start_time=current,
                        end_time=slot_end,
                        is_booked=False
                    )
                    db.add(slot)
                    created_slots.append(slot)

                current = slot_end

        return created_slots


    # =========================================================
    # GET AVAILABLE SLOTS
    # =========================================================
    @staticmethod
    async def get_available_slots(
        db: AsyncSession,
        doctor_id: int,
        target_date: date
    ) -> List[DoctorAvailabilitySlot]:

        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        existing_query = await db.execute(
            select(DoctorAvailabilitySlot).where(
                DoctorAvailabilitySlot.doctor_id == doctor_id,
                DoctorAvailabilitySlot.start_time >= day_start,
                DoctorAvailabilitySlot.start_time < day_end
            )
        )

        existing_slots = existing_query.scalars().all()

        # Auto generate if not exists
        if not existing_slots:
            await SlotService.generate_slots_for_day(
                db=db,
                doctor_id=doctor_id,
                target_date=target_date
            )

        result = await db.execute(
            select(DoctorAvailabilitySlot).where(
                DoctorAvailabilitySlot.doctor_id == doctor_id,
                DoctorAvailabilitySlot.is_booked == False,
                DoctorAvailabilitySlot.start_time >= day_start,
                DoctorAvailabilitySlot.start_time < day_end
            ).order_by(DoctorAvailabilitySlot.start_time)
        )

        return result.scalars().all()


    # =========================================================
    # GET BY DEPARTMENT (BOT)
    # =========================================================
    @staticmethod
    async def get_available_slots_by_department(
        db: AsyncSession,
        department: str,
        target_date: date
    ) -> Tuple[Optional[Doctor], List[DoctorAvailabilitySlot]]:

        doctor_query = await db.execute(
            select(Doctor).where(
                Doctor.department.ilike(f"%{department}%"),
                Doctor.is_active == True
            )
        )

        doctor = doctor_query.scalar_one_or_none()

        if not doctor:
            return None, []

        slots = await SlotService.get_available_slots(
            db=db,
            doctor_id=doctor.id,
            target_date=target_date
        )

        return doctor, slots


    # =========================================================
    # ADMIN: REGENERATE SLOTS (FIXED - NO BEGIN)
    # =========================================================
    @staticmethod
    async def regenerate_slots_for_day(
        db: AsyncSession,
        doctor_id: int,
        target_date: date
    ):

        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        # Delete unbooked slots only
        delete_query = await db.execute(
            select(DoctorAvailabilitySlot).where(
                DoctorAvailabilitySlot.doctor_id == doctor_id,
                DoctorAvailabilitySlot.start_time >= day_start,
                DoctorAvailabilitySlot.start_time < day_end,
                DoctorAvailabilitySlot.is_booked == False
            )
        )

        slots_to_delete = delete_query.scalars().all()

        for slot in slots_to_delete:
            await db.delete(slot)

        # Regenerate
        return await SlotService.generate_slots_for_day(
            db=db,
            doctor_id=doctor_id,
            target_date=target_date
        )