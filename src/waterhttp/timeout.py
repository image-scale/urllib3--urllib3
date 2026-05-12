from __future__ import annotations

import time
import typing
from enum import Enum
from socket import getdefaulttimeout

from .exceptions import TimeoutStateError


class _DefaultSentinel(Enum):
    token = -1


DEFAULT_TIMEOUT: typing.Final[_DefaultSentinel] = _DefaultSentinel.token

_TimeoutValue = typing.Optional[typing.Union[float, _DefaultSentinel]]


class Timeout:
    DEFAULT_TIMEOUT: _TimeoutValue = DEFAULT_TIMEOUT

    def __init__(
        self,
        total: _TimeoutValue = None,
        connect: _TimeoutValue = DEFAULT_TIMEOUT,
        read: _TimeoutValue = DEFAULT_TIMEOUT,
    ) -> None:
        self._connect = self._check_timeout(connect, "connect")
        self._read = self._check_timeout(read, "read")
        self.total = self._check_timeout(total, "total")
        self._start_connect: float | None = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(connect={self._connect!r}, "
            f"read={self._read!r}, total={self.total!r})"
        )

    __str__ = __repr__

    @staticmethod
    def resolve_default_timeout(timeout: _TimeoutValue) -> float | None:
        if timeout is DEFAULT_TIMEOUT:
            return getdefaulttimeout()
        return timeout

    @classmethod
    def _check_timeout(cls, value: _TimeoutValue, name: str) -> _TimeoutValue:
        if value is None or value is DEFAULT_TIMEOUT:
            return value

        if isinstance(value, bool):
            raise ValueError(
                "Timeout cannot be a boolean value. It must "
                "be an int, float or None."
            )
        try:
            float(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            ) from None

        try:
            if value <= 0:
                raise ValueError(
                    "Attempted to set %s timeout to %s, but the "
                    "timeout cannot be set to a value less "
                    "than or equal to 0." % (name, value)
                )
        except TypeError:
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            ) from None

        return value

    @classmethod
    def from_float(cls, timeout: _TimeoutValue) -> Timeout:
        return Timeout(read=timeout, connect=timeout)

    def clone(self) -> Timeout:
        return Timeout(connect=self._connect, read=self._read, total=self.total)

    def start_connect(self) -> float:
        if self._start_connect is not None:
            raise TimeoutStateError("Timeout timer has already been started.")
        self._start_connect = time.monotonic()
        return self._start_connect

    def get_connect_duration(self) -> float:
        if self._start_connect is None:
            raise TimeoutStateError(
                "Can't get connect duration for timer that has not started."
            )
        return time.monotonic() - self._start_connect

    @property
    def connect_timeout(self) -> _TimeoutValue:
        if self.total is None:
            return self._connect

        if self._connect is None or self._connect is DEFAULT_TIMEOUT:
            return self.total

        return min(self._connect, self.total)  # type: ignore[type-var]

    @property
    def read_timeout(self) -> float | None:
        if (
            self.total is not None
            and self.total is not DEFAULT_TIMEOUT
            and self._read is not None
            and self._read is not DEFAULT_TIMEOUT
        ):
            if self._start_connect is None:
                return self._read
            return max(0, min(self.total - self.get_connect_duration(), self._read))
        elif self.total is not None and self.total is not DEFAULT_TIMEOUT:
            return max(0, self.total - self.get_connect_duration())
        else:
            return self.resolve_default_timeout(self._read)
