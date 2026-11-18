"""Hash de senhas (Argon2) e emissão/validação de tokens JWT."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.models.enums import UserRole
from app.schemas.auth import TokenPayload

TokenType = Literal["access", "refresh"]

_password_hash = PasswordHash.recommended()
# Hash "falso" usado quando o e-mail não existe, para o tempo de resposta não revelar
# se o usuário está cadastrado (mitiga enumeração de contas).
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if hashed is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, hashed)


def _create_token(user_id: uuid.UUID, role: UserRole, token_type: TokenType, expires: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    return _create_token(
        user_id, role, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: uuid.UUID, role: UserRole) -> str:
    return _create_token(user_id, role, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    try:
        data = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
        payload = TokenPayload.model_validate(data)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Sessão expirada. Faça login novamente.", code="token_expired") from exc
    except (jwt.InvalidTokenError, ValidationError) as exc:
        raise UnauthorizedError("Token inválido.", code="invalid_token") from exc

    if payload.type != expected_type:
        raise UnauthorizedError("Tipo de token inválido.", code="invalid_token")
    return payload
