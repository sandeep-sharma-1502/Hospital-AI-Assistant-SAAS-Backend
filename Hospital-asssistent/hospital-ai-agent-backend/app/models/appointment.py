from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from app.db.base import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    patient_name = Column(String, nullable=False)
    phone_number = Column(String(15), nullable=False)

    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)

    availability_slot_id = Column(
        Integer,
        ForeignKey("doctor_availability_slots.id"),
        nullable=False
    )

    email = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    reason_for_visit = Column(String, nullable=True)

    status = Column(String, default="scheduled", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )