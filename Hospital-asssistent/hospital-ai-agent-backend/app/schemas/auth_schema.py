from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class LoginRequest(BaseModel):
    """
    Schema for the login request body.
    Expects JSON: {"email": "...", "password": "..."}
    """
    email: EmailStr
    password: str

class Token(BaseModel):
    """
    Schema for the successful login response.
    Returns the JWT and the type.
    """
class Token(BaseModel):
    access_token: str
    token_type: str
    email: str
    full_name: str | None = None
    is_superuser: bool

class TokenPayload(BaseModel):
    """
    Schema for the internal JWT payload.
    'sub' (subject) usually holds the user's email or ID.
    """
    sub: Optional[str] = None
    
    # Optional: Add extra claims if you store roles in the token
    # is_superuser: bool = False

class UserResponse(BaseModel):
    """
    Optional: If you want to return user details alongside the token.
    """
    email: EmailStr
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)