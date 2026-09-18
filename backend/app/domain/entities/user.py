import uuid
from dataclasses import dataclass

from app.domain.roles import Role


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    password_hash: str
    full_name: str | None
    role: Role
    is_active: bool
    total_points: int
    level: int
