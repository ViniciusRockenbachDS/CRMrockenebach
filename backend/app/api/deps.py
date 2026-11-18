"""Dependências compartilhadas pelos endpoints (sessão, usuário logado, permissões, paginação)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.common import PaginationParams

DbSession = Annotated[AsyncSession, Depends(get_db)]

# tokenUrl aponta para o endpoint de formulário usado pelo botão "Authorize" do Swagger.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token", auto_error=False)


async def get_current_user(
    db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]
) -> User:
    if not token:
        raise UnauthorizedError("Não autenticado.")
    payload = decode_token(token, "access")
    user = await db.get(User, UUID(str(payload.sub)))
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuário inválido ou inativo.", code="invalid_user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def _checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return _checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
ManagerUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=settings.PAGINATION_MAX_LIMIT)] = settings.PAGINATION_DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


def get_request_context(request: Request) -> dict[str, Any]:
    """Contexto gravado na auditoria."""
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:255],
        "path": request.url.path,
    }


RequestContext = Annotated[dict[str, Any], Depends(get_request_context)]
