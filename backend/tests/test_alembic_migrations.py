from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings


def test_alembic_upgrade_head_smoke() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    original_database_url = settings.database_url
    settings.database_url = "sqlite+pysqlite:///:memory:"
    config = Config(str(backend_root / "alembic.ini"))
    config.config_file_name = None
    config.set_main_option("script_location", str(backend_root / "migrations"))
    try:
        command.upgrade(config, "head")
    finally:
        settings.database_url = original_database_url
