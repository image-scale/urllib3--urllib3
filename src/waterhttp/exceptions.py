from __future__ import annotations


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
