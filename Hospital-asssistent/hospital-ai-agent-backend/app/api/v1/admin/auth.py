from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError

from fastapi import Request
from app.services.audit_service import log_action

from app.db.database import get_db
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.core.security import (
    verify_password,
    create_access_token,
    decode_token
)
from app.schemas.auth_schema import LoginRequest, Token
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["admin-auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# 🔐 LOGIN ROUTE (Production Grade)
@router.post("/login", response_model=Token)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Login attempt for: {data.email}")

    # 1️⃣ Fetch user
    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    user = result.scalars().first()

    # 2️⃣ Validate credentials
    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning(f"Invalid login attempt for: {data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # 3️⃣ Check account active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # 4️⃣ Admin check
    if not getattr(user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have administrative privileges"
        )

    # 5️⃣ Generate token
    access_token = create_access_token(
        subject=user.email,
        extra_claims={
            "full_name": user.full_name,
        }
    )

    logger.info(f"Admin login successful: {user.email}")
    
        # ✅ Audit log
    await log_action(
        db=db,
        user_email=user.email,
        action="Admin Login",
        ip_address=request.client.host
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": user.email,
        "full_name": user.full_name,
        "is_superuser": user.is_superuser
    }


# 🔐 LOGOUT ROUTE (Blacklist Based)
@router.post("/logout")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        email = payload.get("sub")

        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # 🔴 Add to blacklist
    blacklisted_token = TokenBlacklist(jti=jti)
    db.add(blacklisted_token)
    await db.commit()
    
        # ✅ Audit log
    await log_action(
        db=db,
        user_email=email,
        action="Admin Logout",
        ip_address=request.client.host
    )

    logger.info("User logged out and token revoked.")

    return {"message": "Successfully logged out"}