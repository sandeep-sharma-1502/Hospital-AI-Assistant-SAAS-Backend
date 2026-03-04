from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# --------------------------------------------------
# 🔐 Engine Configuration (Production Ready)
# --------------------------------------------------

engine = create_async_engine(
    settings.database_url,

    # 🔕 Disable SQL logs in production
    echo=(settings.ENVIRONMENT == "development"),

    # 🔄 Pool Settings
    pool_pre_ping=True,        # Checks if connection is alive
    pool_size=10,              # Default active connections
    max_overflow=20,           # Extra connections beyond pool_size
    pool_timeout=30,           # Wait time before connection timeout

    # Async optimization
    future=True,
)

# --------------------------------------------------
# 🗄 Session Factory
# --------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# --------------------------------------------------
# 📦 Base Model (SQLAlchemy 2.0)
# --------------------------------------------------

# class Base(DeclarativeBase):
#     pass


# --------------------------------------------------
# 🔗 FastAPI Dependency
# --------------------------------------------------

async def get_db():
    """
    Provides a database session per request.
    Session is automatically closed after request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()