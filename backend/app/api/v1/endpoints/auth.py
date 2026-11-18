from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession, RequestContext
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenPair
from app.schemas.common import MessageResponse
from app.schemas.user import PasswordChange, UserRead, UserSelfUpdate
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=LoginResponse, summary="Login com e-mail e senha (JSON)")
async def login(data: LoginRequest, db: DbSession, context: RequestContext) -> LoginResponse:
    user = await user_service.authenticate(db, data.email, data.password, context)
    return LoginResponse(**_tokens(user).model_dump(), user=UserRead.model_validate(user))


@router.post(
    "/token",
    response_model=TokenPair,
    summary="Login via formulário OAuth2 (usado pelo botão Authorize do Swagger)",
)
async def token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession, context: RequestContext
) -> TokenPair:
    user = await user_service.authenticate(db, form.username.lower(), form.password, context)
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair, summary="Renova o access token")
async def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    payload = decode_token(data.refresh_token, "refresh")
    user = await db.get(User, payload.sub)
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuário inválido ou inativo.", code="invalid_user")
    return _tokens(user)


@router.get("/me", response_model=UserRead, summary="Usuário logado")
async def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead, summary="Atualiza o próprio perfil")
async def update_me(data: UserSelfUpdate, db: DbSession, user: CurrentUser, context: RequestContext) -> User:
    return await user_service.update_user(db, user.id, data, user, context)


@router.post("/me/password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def change_password(data: PasswordChange, db: DbSession, user: CurrentUser) -> MessageResponse:
    await user_service.change_password(db, user, data)
    return MessageResponse(message="Senha alterada com sucesso.")
