import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field

from app.models.enums import UserRole
from app.schemas.common import InputModel, TimestampedRead
from app.schemas.types import LowerEmail


def _validate_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("A senha deve conter letras e números.")
    return value


Password = Annotated[
    str,
    Field(min_length=8, max_length=128),
    AfterValidator(_validate_password_strength),
]
UserName = Annotated[str, Field(min_length=2, max_length=120)]


class UserCreate(InputModel):
    name: UserName
    email: LowerEmail
    password: Password
    role: UserRole = UserRole.SALES


class UserUpdate(InputModel):
    """Atualização feita por administrador."""

    name: UserName | None = None
    email: LowerEmail | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserSelfUpdate(InputModel):
    """Atualização do próprio perfil (sem alterar papel/ativação)."""

    name: UserName | None = None
    email: LowerEmail | None = None


class PasswordChange(InputModel):
    current_password: str = Field(min_length=1)
    new_password: Password


class UserRead(TimestampedRead):
    name: str
    email: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
