from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.signals import list_signals


def test_list_signals_starts_empty(db_session_factory: sessionmaker[Session]) -> None:
    with db_session_factory() as db:
        assert list_signals(db=db) == []
