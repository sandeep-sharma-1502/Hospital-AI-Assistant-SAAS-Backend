from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("/db-schema")
async def get_db_schema(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = text("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)

    result = await db.execute(query)
    rows = result.fetchall()

    schema = {}

    for table_name, column_name, data_type in rows:
        if table_name not in schema:
            schema[table_name] = []

        schema[table_name].append({
            "column": column_name,
            "type": data_type
        })

    return schema


@router.get("/db-check")
async def check_db(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # 1️⃣ Database Time
    time_result = await db.execute(text("SELECT NOW();"))
    db_time = time_result.scalar()

    # 2️⃣ Count Users (no sensitive data)
    user_count_result = await db.execute(text("SELECT COUNT(*) FROM users;"))
    total_users = user_count_result.scalar()

    # 3️⃣ Count Audit Logs
    audit_count_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs;"))
    total_audit_logs = audit_count_result.scalar()

    # 4️⃣ Count Blacklisted Tokens
    blacklist_count_result = await db.execute(text("SELECT COUNT(*) FROM token_blacklist;"))
    total_blacklisted_tokens = blacklist_count_result.scalar()

    return {
        "status": "connected",
        "database_time": db_time,
        "total_users": total_users,
        "total_audit_logs": total_audit_logs,
        "total_blacklisted_tokens": total_blacklisted_tokens
    }