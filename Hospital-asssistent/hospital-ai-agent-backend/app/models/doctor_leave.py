from sqlalchemy import Column, Integer, Date, ForeignKey, String
from app.db.base import Base


class DoctorLeave(Base):
    __tablename__ = "doctor_leaves"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)

    leave_date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)