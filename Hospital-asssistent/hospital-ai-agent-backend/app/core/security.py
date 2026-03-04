from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
from uuid import uuid4

from app.core.config import settings


# 1️⃣ Password hashing configuration
# Using bcrypt (high security standard)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # stronger hashing rounds
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if a plain text password matches the hashed version from the DB.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Creates a secure bcrypt hash of a password.
    """
    return pwd_context.hash(password)


# 2️⃣ Create Access Token (Enhanced)
def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a JWT token (Access or Refresh).
    - subject: Usually user's email or ID.
    - expires_delta: Custom expiration.
    - token_type: 'access' or 'refresh'
    """

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    now = datetime.now(timezone.utc)

    # Standard + Security Claims
    to_encode: Dict[str, Any] = {
        "exp": expire,
        "sub": str(subject),
        "iat": now,
        "iss": "hospital-ai",           # issuer
        "aud": "hospital-admin",        # audience
        "type": token_type,             # token type
        "jti": str(uuid4())             # unique token id (for blacklist)
    }
        # 🔥 Add custom claims safely
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


# 3️⃣ Decode & Validate Token (Senior Level)
def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Raises JWTError if invalid.
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience="hospital-admin"
        )

        return payload

    except JWTError as e:
        raise JWTError(f"Token validation failed: {str(e)}")


# 4️⃣ Create Refresh Token (Longer Expiry)
def create_refresh_token(subject: Union[str, Any]) -> str:
    """
    Generates a long-lived refresh token.
    """

    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    return create_access_token(
        subject=subject,
        expires_delta=expire - datetime.now(timezone.utc),
        token_type="refresh"
    )