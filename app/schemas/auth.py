from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr


class RoleEnum(str, Enum):
    admin = "admin"
    employer = "employer"
    candidate = "candidate"


class RegisterRequest(BaseModel):
    email: EmailStr | None = None
    password: str
    role: RoleEnum
    phone: str | None = None
    first_name: str | None = None
    surname: str | None = None


class LoginRequest(BaseModel):
    email: str | None = None
    password: str
    phone: str | None = None
    login_type: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str | None = None
    phone: str | None = None
    role: RoleEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateEmailRequest(BaseModel):
    new_email: str | None = None
    current_password: str
