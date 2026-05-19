from app.api.routes.signals import list_signals


def test_list_signals_starts_empty() -> None:
    assert list_signals() == []

