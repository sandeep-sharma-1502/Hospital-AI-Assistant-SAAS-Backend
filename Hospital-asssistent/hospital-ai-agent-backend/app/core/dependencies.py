from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError

from app.db.database import get_db
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.core.security import decode_token
from app.core.logging import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------
# 🔐 Get Current Authenticated User
# ---------------------------------------------------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:

    try:
        payload = decode_token(token)

        email: str | None = payload.get("sub")
        jti: str | None = payload.get("jti")

        if email is None or jti is None:
            logger.warning("Invalid token payload structure")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError:
        logger.warning("JWT decode failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -----------------------------------------------------
    # 🔴 Check Token Blacklist (Logout Protection)
    # -----------------------------------------------------
    result = await db.execute(
        select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    )
    blacklisted = result.scalars().first()

    if blacklisted:
        logger.info(f"Blocked blacklisted token for {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -----------------------------------------------------
    # 🟢 Load User From Database
    # -----------------------------------------------------
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalars().first()

    if not user:
        logger.warning(f"User not found for token subject: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


# ---------------------------------------------------------
# 🛡 Require Admin Role
# ---------------------------------------------------------
async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:

    if not current_user.is_superuser:
        logger.warning(
            f"Non-admin user attempted admin access: {current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user