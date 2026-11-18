from fastapi import APIRouter

from app.api.v1.endpoints import ai, auth, clients, dashboard, deals, meta, payments, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(clients.router)
api_router.include_router(deals.router)
api_router.include_router(payments.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(meta.router)
