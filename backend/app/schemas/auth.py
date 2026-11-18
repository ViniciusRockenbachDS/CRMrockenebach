from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import UserRole
from app.schemas.common import InputModel
from app.schemas.types import LowerEmail
from app.schemas.user import UserRead


class LoginRequest(InputModel):
    email: LowerEmail
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(InputModel):
    refresh_token: str = Field(min_length=10)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Validade do access token em segundos")


class LoginResponse(TokenPair):
    user: UserRead


class TokenPayload(BaseModel):
    """Claims do JWT."""

    sub: UUID
    type: Literal["access", "refresh"]
    role: UserRole
    exp: int
    iat: int
    jti: str | None = None  # id do token (permite revogação futura via blocklist)
