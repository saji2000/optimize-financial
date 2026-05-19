from typing import Any


def require_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Expected structured object output")
    return payload

