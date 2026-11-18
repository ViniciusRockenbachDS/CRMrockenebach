from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import DashboardFilters, DashboardResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse, summary="KPIs, funil, receita e inadimplência")
async def get_dashboard(
    db: DbSession, _: CurrentUser, filters: Annotated[DashboardFilters, Query()]
) -> DashboardResponse:
    return await dashboard_service.get_dashboard(db, filters)
