import os

# Pin the test suite to the OpenAI provider so the existing OpenAI-path
# assertions (Responses API, service_tier, gpt-5.x model defaults) stay valid
# regardless of the runtime default in .env. Must run before app.core.config is
# imported below so the settings singleton picks it up. DeepSeek-path behavior
# is covered explicitly in test_deepseek_provider.py.
os.environ["LLM_PROVIDER"] = "openai"

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base


@pytest.fixture()
def db_session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    try:
        yield testing_session_factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
