import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, Pagination, RequestContext
from app.models import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get("", response_model=Page[UserRead], summary="Lista usuários (para filtros e responsáveis)")
async def list_users(
    db: DbSession,
    _: CurrentUser,
    page: Pagination,
    search: str | None = Query(default=None, max_length=100),
    only_active: bool = False,
) -> Page[UserRead]:
    return await user_service.list_users(db, page, search, only_active)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Cria usuário (admin)")
async def create_user(data: UserCreate, db: DbSession, admin: AdminUser, context: RequestContext) -> User:
    return await user_service.create_user(db, data, admin, context)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, db: DbSession, _: CurrentUser) -> User:
    return await user_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead, summary="Atualiza usuário (admin)")
async def update_user(
    user_id: uuid.UUID, data: UserUpdate, db: DbSession, admin: AdminUser, context: RequestContext
) -> User:
    return await user_service.update_user(db, user_id, data, admin, context)
