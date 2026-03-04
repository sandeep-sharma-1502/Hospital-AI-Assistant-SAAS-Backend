from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Unique user/device identifier (WebRTC or frontend session ID)
    user_identifier = Column(String, nullable=True, index=True)

    # Booking State Machine
    booking_stage = Column(String, nullable=True)
    booking_data = Column(JSON, nullable=True, default=dict)

    # Session lifecycle
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    last_activity_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    is_active = Column(Boolean, default=True)