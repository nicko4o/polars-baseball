class PolarsBaseballError(Exception):
    """Base exception for all polars_baseball errors."""


class ClientError(PolarsBaseballError):
    """4xx-equivalent: invalid input, caller's fault."""


class ServerError(PolarsBaseballError):
    """5xx-equivalent: upstream / parsing failure, not caller's fault."""


class PolarsBaseballHttpError(ServerError):
    """Exception raised when an HTTP request fails."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class PolarsBaseballTransportError(ServerError):
    """Exception raised when no HTTP response was received."""


class InvalidParameterError(ClientError, ValueError):
    """Exception raised when query parameters are invalid (4xx equivalent)."""

    pass


class UpstreamParseError(ServerError, RuntimeError):
    """Exception raised when parsing upstream data fails (5xx equivalent)."""

    pass


class UpstreamStructureChangedError(UpstreamParseError):
    """Exception raised when upstream website layout or JSON structure changes (5xx equivalent)."""

    pass


class UpstreamDataCorruptedError(UpstreamParseError):
    """Exception raised when downloaded upstream data is corrupted or unreadable (5xx equivalent)."""

    pass


class InvalidSchemaError(ServerError):
    """Exception raised when schema validation fails (5xx equivalent)."""

    pass


class CacheClearError(ServerError):
    """Exception raised when clearing the cache fails (5xx equivalent)."""

    pass


class UpstreamUnavailableError(ServerError):
    """Exception raised when upstream service returns empty response or is unavailable."""

    pass
