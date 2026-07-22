from typing import TypeVar

_T = TypeVar("_T")


def ensure_str(data: str | bytes) -> str:
    if isinstance(data, str):
        return data
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def ensure_bytes(data: str | bytes) -> bytes:
    return data if isinstance(data, bytes) else data.encode("utf-8")
