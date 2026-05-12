from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .connectionpool import HTTPPool


class HTTPError(Exception):
    pass


class HTTPWarning(UserWarning):
    pass


class LocationValueError(ValueError, HTTPError):
    pass


class LocationParseError(LocationValueError):
    def __init__(self, location: str | object) -> None:
        message = f"Failed to parse: {location!r}"
        super().__init__(message)
        self.location = location


class TimeoutStateError(HTTPError):
    pass


class TimeoutError(HTTPError):
    pass


class ConnectTimeoutError(TimeoutError):
    pass


class ReadTimeoutError(TimeoutError):
    pass


class ProtocolError(HTTPError):
    pass


class SSLError(HTTPError):
    pass


class ProxyError(HTTPError):
    def __init__(self, message: str, error: Exception | None = None) -> None:
        super().__init__(message, error)
        self.original_error = error


class PoolError(HTTPError):
    def __init__(self, pool: HTTPPool, message: str) -> None:
        super().__init__(f"{pool}: {message}")
        self.pool = pool


class RequestError(PoolError):
    def __init__(self, pool: HTTPPool, url: str, message: str) -> None:
        super().__init__(pool, message)
        self.url = url


class MaxRetryError(RequestError):
    def __init__(
        self, pool: HTTPPool | None, url: str | None, reason: Exception | None = None
    ) -> None:
        self.pool = pool  # type: ignore[assignment]
        self.url = url  # type: ignore[assignment]
        self.reason = reason
        message = f"Max retries exceeded with url: {url} (Caused by {reason!r})"
        HTTPError.__init__(self, message)


class ResponseError(HTTPError):
    GENERIC_ERROR = "too many error responses"
    SPECIFIC_ERROR = "too many {status_code} error responses"


class HostChangedError(RequestError):
    pass


class EmptyPoolError(PoolError):
    pass


class FullPoolError(PoolError):
    pass


class ClosedPoolError(PoolError):
    pass


class NewConnectionError(ConnectTimeoutError):
    def __init__(self, conn: object, message: str) -> None:
        self.conn = conn
        super().__init__(message)


class InvalidHeader(HTTPError):
    pass


class DecodeError(HTTPError):
    pass


class SecurityWarning(HTTPWarning):
    pass


class InsecureRequestWarning(SecurityWarning):
    pass


class NotOpenSSLWarning(SecurityWarning):
    pass


class InsecurePlatformWarning(SecurityWarning):
    pass


class DependencyWarning(HTTPWarning):
    pass


class BodyNotHttplibCompatible(HTTPError):
    pass


class IncompleteRead(HTTPError):
    def __init__(self, partial: int, expected: int) -> None:
        self.partial = partial
        self.expected = expected
        super().__init__(f"{partial} bytes read, {expected} more expected")


class ResponseNotChunked(ProtocolError, ValueError):
    pass


class InvalidChunkLength(HTTPError):
    pass


class UnrewindableBodyError(HTTPError):
    pass


class URLSchemeUnknown(LocationValueError):
    def __init__(self, scheme: str) -> None:
        super().__init__(f"Not supported URL scheme {scheme}")
        self.scheme = scheme


class ProxySchemeUnknown(URLSchemeUnknown):
    pass
