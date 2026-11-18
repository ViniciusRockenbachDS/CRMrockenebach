"""Prepara o banco em um único comando (dentro de backend/, com o venv ativo):

    python -m app.scripts.init_db

1. Aplica as migrations existentes (a 0001 habilita a extensão pg_trgm).
2. Na primeira execução, gera a migration do schema a partir dos models
   (alembic --autogenerate) e a aplica — criando tabelas, enums e índices.

Depois disso, alterações futuras nos models seguem o fluxo padrão:
    alembic revision --autogenerate -m "descricao"
    alembic upgrade head
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[2]


def main() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    print("[1/3] Aplicando migrations existentes...")
    command.upgrade(config, "head")

    versions = [p for p in (BACKEND_DIR / "alembic" / "versions").glob("*.py") if not p.name.startswith("__")]
    if len(versions) <= 1:
        print("[2/3] Gerando a migration do schema a partir dos models...")
        command.revision(config, message="schema inicial", autogenerate=True)
        print("[3/3] Criando tabelas, enums e índices...")
        command.upgrade(config, "head")
    else:
        print("[2/3] Migration do schema já existe — nada a gerar.")
        print("[3/3] Banco atualizado.")
    print("[ok] Banco pronto. Próximo passo: python -m app.scripts.seed --demo")


if __name__ == "__main__":
    main()
