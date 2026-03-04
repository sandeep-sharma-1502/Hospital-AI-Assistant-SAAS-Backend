from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    user_email: str,
    action: str,
    ip_address: str | None = None
):
    audit = AuditLog(
        user_email=user_email,
        action=action,
        ip_address=ip_address
    )

    db.add(audit)
    await db.commit()