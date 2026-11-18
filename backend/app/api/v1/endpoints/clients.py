import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, ManagerUser, Pagination, RequestContext
from app.models import Client, Interaction
from app.schemas.client import ClientCreate, ClientDetail, ClientFilters, ClientListItem, ClientRead, ClientUpdate
from app.schemas.common import Page
from app.schemas.interaction import InteractionCreate, InteractionFilters, InteractionRead, InteractionUpdate
from app.services import client_service

router = APIRouter(prefix="/clients", tags=["Clientes"])


@router.get("", response_model=Page[ClientListItem], summary="Lista clientes com filtros e busca")
async def list_clients(
    db: DbSession, _: CurrentUser, page: Pagination, filters: Annotated[ClientFilters, Query()]
) -> Page[ClientListItem]:
    return await client_service.list_clients(db, filters, page)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(data: ClientCreate, db: DbSession, user: CurrentUser, context: RequestContext) -> Client:
    return await client_service.create_client(db, data, user, context)


@router.get("/{client_id}", response_model=ClientDetail, summary="Cliente + estatísticas + interações + negociações")
async def get_client(client_id: uuid.UUID, db: DbSession, _: CurrentUser) -> ClientDetail:
    return await client_service.get_client_detail(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: uuid.UUID, data: ClientUpdate, db: DbSession, user: CurrentUser, context: RequestContext
) -> Client:
    return await client_service.update_client(db, client_id, data, user, context)


@router.delete(
    "/{client_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclusão lógica (gestor/admin)"
)
async def delete_client(client_id: uuid.UUID, db: DbSession, user: ManagerUser, context: RequestContext) -> Response:
    await client_service.delete_client(db, client_id, user, context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ interações
@router.get("/{client_id}/interactions", response_model=Page[InteractionRead], tags=["Interações"])
async def list_interactions(
    client_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    page: Pagination,
    filters: Annotated[InteractionFilters, Query()],
) -> Page[InteractionRead]:
    return await client_service.list_interactions(db, client_id, filters, page)


@router.post(
    "/{client_id}/interactions",
    response_model=InteractionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Interações"],
)
async def create_interaction(
    client_id: uuid.UUID, data: InteractionCreate, db: DbSession, user: CurrentUser, context: RequestContext
) -> Interaction:
    return await client_service.create_interaction(db, client_id, data, user, context)


@router.patch("/{client_id}/interactions/{interaction_id}", response_model=InteractionRead, tags=["Interações"])
async def update_interaction(
    client_id: uuid.UUID,
    interaction_id: uuid.UUID,
    data: InteractionUpdate,
    db: DbSession,
    user: CurrentUser,
    context: RequestContext,
) -> Interaction:
    return await client_service.update_interaction(db, client_id, interaction_id, data, user, context)


@router.delete(
    "/{client_id}/interactions/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Interações"]
)
async def delete_interaction(
    client_id: uuid.UUID, interaction_id: uuid.UUID, db: DbSession, user: CurrentUser, context: RequestContext
) -> Response:
    await client_service.delete_interaction(db, client_id, interaction_id, user, context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
