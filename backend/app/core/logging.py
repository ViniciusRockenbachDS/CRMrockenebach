import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # SQL só aparece com DB_ECHO=true (configurado no engine).
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
