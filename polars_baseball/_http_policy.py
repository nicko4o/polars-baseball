from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from polars_baseball._config import BREF_ROOT, FG_ROOT


class TransportKind(Enum):
    HTTPX = "httpx"
    BROWSER = "browser"


@dataclass(frozen=True)
class RequestPolicy:
    transport: TransportKind
    provider_label: str
    rate_limited: bool = False


_DEFAULT_POLICY = RequestPolicy(TransportKind.HTTPX, "HTTP")
_PROVIDER_POLICIES: tuple[tuple[str, RequestPolicy], ...] = (
    (BREF_ROOT, RequestPolicy(TransportKind.BROWSER, "BRef", rate_limited=True)),
    (FG_ROOT, RequestPolicy(TransportKind.BROWSER, "FanGraphs")),
)


def resolve_request_policy(url: str) -> RequestPolicy:
    for root, policy in _PROVIDER_POLICIES:
        if _same_origin(url, root):
            return policy
    return _DEFAULT_POLICY


def _same_origin(url: str, root: str) -> bool:
    parsed_url = urlparse(url)
    parsed_root = urlparse(root)
    return parsed_url.scheme == parsed_root.scheme and parsed_url.hostname == parsed_root.hostname
