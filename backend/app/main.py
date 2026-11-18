"""Ponto de entrada da API: uvicorn app.main:app --reload"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db.session import engine

DESCRIPTION = """
API do **CRM** — gestão de clientes, funil de vendas, pagamentos e camada de IA.

**Como testar pelo Swagger:** clique em **Authorize**, informe o e-mail e a senha do
administrador (definidos no `.env`) e todas as rotas protegidas passam a funcionar.

Todos os erros seguem o formato `{"code", "message", "details"}`.
"""

TAGS = [
    {"name": "Autenticação", "description": "Login, renovação de token e perfil"},
    {"name": "Usuários", "description": "Gestão de usuários (criação/edição: admin)"},
    {"name": "Clientes", "description": "Leads, contatos e clientes"},
    {"name": "Interações", "description": "Histórico de contatos com o cliente"},
    {"name": "Negociações", "description": "Funil de vendas e Kanban"},
    {"name": "Pagamentos", "description": "Faturas, recebimentos e inadimplência"},
    {"name": "Dashboard", "description": "Métricas consolidadas"},
    {"name": "Inteligência Artificial", "description": "Resumos, lead scoring e insights"},
    {"name": "Metadados", "description": "Opções para os formulários do front-end"},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Metadados"], summary="Verifica API e conexão com o banco")
async def health() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "environment": settings.APP_ENV}
