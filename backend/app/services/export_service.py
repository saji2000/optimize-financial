from app.domain.signal_schema import SignalRead


def signals_to_jsonl(signals: list[SignalRead]) -> str:
    return "\n".join(signal.model_dump_json() for signal in signals)

