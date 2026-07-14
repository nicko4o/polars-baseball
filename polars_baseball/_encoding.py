from typing import TypeVar

_T = TypeVar("_T")


def ensure_str(data: str | bytes) -> str:
    return data if isinstance(data, str) else data.decode("utf-8", errors="strict")


def ensure_bytes(data: str | bytes) -> bytes:
    return data if isinstance(data, bytes) else data.encode("utf-8")
