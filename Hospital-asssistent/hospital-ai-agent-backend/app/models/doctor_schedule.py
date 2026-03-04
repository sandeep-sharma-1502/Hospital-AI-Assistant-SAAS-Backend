from sqlalchemy import Column, Integer, Time, ForeignKey, Boolean
from app.db.base import Base


class DoctorWeeklySchedule(Base):
    __tablename__ = "doctor_weekly_schedules"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)

    # 0 = Monday, 6 = Sunday
    weekday = Column(Integer, nullable=False)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    is_active = Column(Boolean, default=True)