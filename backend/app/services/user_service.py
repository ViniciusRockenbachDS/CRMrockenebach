import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models import AuditAction, User, UserRole
from app.schemas.common import Page, PaginationParams
from app.schemas.user import PasswordChange, UserCreate, UserRead, UserSelfUpdate, UserUpdate
from app.services import audit_service
from app.services.common import apply_updates, paginate
from app.utils.dates import now_utc


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado.")
    return user


async def authenticate(db: AsyncSession, email: str, password: str, context: dict[str, Any]) -> User:
    user = await get_by_email(db, email)
    if not verify_password(password, user.hashed_password if user else None) or user is None:
        raise UnauthorizedError("E-mail ou senha incorretos.", code="invalid_credentials")
    if not user.is_active:
        raise UnauthorizedError("Usuário desativado. Procure o administrador.", code="inactive_user")
    user.last_login_at = now_utc()
    await audit_service.log(
        db, entity_type="user", entity_id=user.id, action=AuditAction.LOGIN, user_id=user.id, context=context
    )
    await db.commit()
    await db.refresh(user)  # recarrega updated_at (gerado no banco) sem lazy load em async
    return user


async def list_users(
    db: AsyncSession, page: PaginationParams, search: str | None = None, only_active: bool = False
) -> Page[UserRead]:
    stmt = select(User).order_by(User.name)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(term), User.email.ilike(term)))
    if only_active:
        stmt = stmt.where(User.is_active.is_(True))
    return await paginate(db, stmt, page, UserRead)


async def create_user(
    db: AsyncSession, data: UserCreate, actor: User | None, context: dict[str, Any] | None = None
) -> User:
    if await get_by_email(db, data.email):
        raise ConflictError("Já existe um usuário com este e-mail.")
    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await audit_service.log(
        db,
        entity_type="user",
        entity_id=user.id,
        action=AuditAction.CREATE,
        user_id=actor.id if actor else None,
        changes=audit_service.snapshot(user, ["name", "email", "role"]),
        context=context,
    )
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: UserUpdate | UserSelfUpdate,
    actor: User,
    context: dict[str, Any] | None = None,
) -> User:
    user = await get_user(db, user_id)
    payload = data.model_dump(exclude_unset=True)
    if "email" in payload and payload["email"] and payload["email"] != user.email:
        if await get_by_email(db, payload["email"]):
            raise ConflictError("Já existe um usuário com este e-mail.")
    if user.id == actor.id and (payload.get("is_active") is False or payload.get("role") not in (None, actor.role)):
        raise BusinessRuleError("Você não pode desativar nem alterar o próprio papel.")
    changes = apply_updates(user, payload, non_nullable=("name", "email", "role", "is_active"))
    if changes:
        await audit_service.log(
            db, entity_type="user", entity_id=user.id, action=AuditAction.UPDATE,
            user_id=actor.id, changes=changes, context=context,
        )
        await db.commit()
        await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, data: PasswordChange) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise BusinessRuleError("Senha atual incorreta.", code="wrong_password")
    user.hashed_password = hash_password(data.new_password)
    await audit_service.log(
        db, entity_type="user", entity_id=user.id, action=AuditAction.UPDATE,
        user_id=user.id, changes={"password": {"old": "***", "new": "***"}},
    )
    await db.commit()


async def ensure_first_admin(db: AsyncSession) -> User:
    """Cria o administrador inicial definido no .env (idempotente)."""
    existing = await get_by_email(db, settings.FIRST_ADMIN_EMAIL)
    if existing:
        return existing
    return await create_user(
        db,
        UserCreate(
            name=settings.FIRST_ADMIN_NAME,
            email=settings.FIRST_ADMIN_EMAIL,
            password=settings.FIRST_ADMIN_PASSWORD.get_secret_value(),
            role=UserRole.ADMIN,
        ),
        actor=None,
    )
