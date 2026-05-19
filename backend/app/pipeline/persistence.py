from app.domain.signal_schema import SignalRead


def persist_finalized_signals(signals: list[SignalRead]) -> int:
    return len(signals)

