from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_email = Column(String, nullable=False, index=True)

    action = Column(String, nullable=False)

    ip_address = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)