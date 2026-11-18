"""Engine e fábrica de sessões assíncronas."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # objetos continuam legíveis após o commit (serialização da resposta)
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependência do FastAPI: uma sessão por requisição.

    O commit é responsabilidade da camada de serviço (unidade de trabalho explícita);
    aqui garantimos rollback em caso de erro e o fechamento da sessão.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
