from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class DoctorAvailabilitySlot(Base):
    __tablename__ = "doctor_availability_slots"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)

    # 🔥 Important for booking logic
    is_booked = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    doctor = relationship("Doctor", backref="availability_slots")

    # Composite index (performance boost)
    __table_args__ = (
        Index("ix_doctor_date", "doctor_id", "start_time"),
    )