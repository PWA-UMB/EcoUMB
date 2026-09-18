import uuid
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.roles import Role

BCRYPT_MAX_BYTES = 72
_PASSWORD = Annotated[str, Field(min_length=8, max_length=BCRYPT_MAX_BYTES)]


class _StrictRequest(BaseModel):
    """Rechaza campos desconocidos: impide, p. ej., enviar ``role`` al registrarse."""

    model_config = ConfigDict(extra="forbid")


class RegisterRequest(_StrictRequest):
    email: EmailStr
    password: _PASSWORD
    full_name: Annotated[str | None, Field(max_length=120)] = None

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("full_name")
    @classmethod
    def _blank_name_is_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @field_validator("password")
    @classmethod
    def _password_is_strong(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError("La contraseña no puede superar los 72 bytes")
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("La contraseña debe incluir al menos una letra y un número")
        return value


class LoginRequest(_StrictRequest):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class RefreshRequest(_StrictRequest):
    refresh_token: Annotated[str, Field(min_length=1, max_length=4096)]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: Role
    total_points: int
    level: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
