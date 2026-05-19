from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def run_with_retries(operation: Callable[[], T], attempts: int = 3) -> T:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
    if last_error is None:
        raise ValueError("attempts must be greater than zero")
    raise last_error

