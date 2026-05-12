from __future__ import annotations

import logging
import queue
import typing
from types import TracebackType

from .connection import HTTPConnection, HTTPSConnection, SCHEME_TO_PORT, is_connection_dropped
from .datastructures import HTTPHeaderDict
from .exceptions import (
    ClosedPoolError,
    EmptyPoolError,
    FullPoolError,
    LocationValueError,
)
from .request_methods import RequestMethods
from .retry import Retry
from .timeout import Timeout, DEFAULT_TIMEOUT, _DefaultSentinel
from .url import Url, parse_url, _normalize_host

log = logging.getLogger(__name__)


class BasePool:
    scheme: str | None = None
    QueueCls = queue.LifoQueue

    def __init__(self, host: str, port: int | None = None) -> None:
        if not host:
            raise LocationValueError("No host specified.")
        self.host = _normalize_host(host, scheme=self.scheme)
        self.port = port

    def __str__(self) -> str:
        return f"{type(self).__name__}(host={self.host!r}, port={self.port!r})"

    def __enter__(self) -> BasePool:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> typing.Literal[False]:
        self.close()
        return False

    def close(self) -> None:
        pass


class HTTPPool(BasePool, RequestMethods):
    scheme = "http"
    ConnectionCls: type[HTTPConnection] = HTTPConnection

    def __init__(
        self,
        host: str,
        port: int | None = None,
        timeout: Timeout | float | _DefaultSentinel | None = DEFAULT_TIMEOUT,
        maxsize: int = 1,
        block: bool = False,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        _proxy: Url | None = None,
        _proxy_headers: typing.Mapping[str, str] | None = None,
        **conn_kw: typing.Any,
    ):
        BasePool.__init__(self, host, port)
        RequestMethods.__init__(self, headers)

        if not isinstance(timeout, Timeout):
            timeout = Timeout.from_float(timeout)

        if retries is None:
            retries = Retry.DEFAULT

        self.timeout = timeout
        self.retries = retries

        self.pool: queue.LifoQueue[typing.Any] | None = self.QueueCls(maxsize)
        self.block = block

        self.proxy = _proxy
        self.proxy_headers = _proxy_headers or {}

        for _ in range(maxsize):
            self.pool.put(None)

        self.num_connections = 0
        self.num_requests = 0
        self.conn_kw = conn_kw

    def _new_conn(self) -> HTTPConnection:
        self.num_connections += 1
        log.debug(
            "Starting new HTTP connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "80",
        )
        conn = self.ConnectionCls(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            **self.conn_kw,
        )
        return conn

    def _get_conn(self, timeout: float | None = None) -> HTTPConnection:
        conn = None
        if self.pool is None:
            raise ClosedPoolError(self, "Pool is closed.")

        try:
            conn = self.pool.get(block=self.block, timeout=timeout)
        except AttributeError:
            raise ClosedPoolError(self, "Pool is closed.") from None
        except queue.Empty:
            if self.block:
                raise EmptyPoolError(
                    self,
                    "Pool is empty and a new connection can't be opened due to blocking mode.",
                ) from None

        if conn and is_connection_dropped(conn):
            log.debug("Resetting dropped connection: %s", self.host)
            conn.close()
            conn = None

        return conn or self._new_conn()

    def _return_conn(self, conn: HTTPConnection | None) -> None:
        if self.pool is not None:
            try:
                self.pool.put(conn, block=False)
                return
            except AttributeError:
                pass
            except queue.Full:
                if conn:
                    conn.close()
                if self.block:
                    raise FullPoolError(
                        self,
                        "Pool reached maximum size and no more connections are allowed.",
                    ) from None
                log.warning(
                    "Connection pool is full, discarding connection: %s.",
                    self.host,
                )
                return

        if conn:
            conn.close()

    def close(self) -> None:
        if self.pool is None:
            return
        old_pool, self.pool = self.pool, None
        try:
            while True:
                conn = old_pool.get(block=False)
                if conn:
                    conn.close()
        except queue.Empty:
            pass

    def is_same_host(self, url: str) -> bool:
        parsed = parse_url(url)
        scheme = (parsed.scheme or "http").lower()
        host = parsed.host
        port = parsed.port

        if host is not None:
            host = _normalize_host(host, scheme=scheme)

        if self.port and not port:
            port = SCHEME_TO_PORT.get(scheme)

        if not self.port and not port:
            return scheme == (self.scheme or "http") and host == self.host

        return (
            scheme == (self.scheme or "http")
            and host == self.host
            and port == self.port
        )

    def urlopen(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        redirect: bool = True,
        timeout: Timeout | float | _DefaultSentinel | None = DEFAULT_TIMEOUT,
        **response_kw: typing.Any,
    ) -> typing.Any:
        if headers is None:
            headers = self.headers

        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        conn = self._get_conn()
        self.num_requests += 1

        try:
            if not isinstance(timeout, Timeout):
                timeout = Timeout.from_float(timeout)

            timeout_obj = timeout.clone()
            timeout_obj.start_connect()
            conn.timeout = timeout_obj.connect_timeout

            conn.request(method, url, body=body, headers=dict(headers) if headers else {})
            response = conn.getresponse()

            from .response import WaterHTTPResponse
            resp = WaterHTTPResponse.from_httplib(response)
            self._return_conn(conn)
            return resp

        except Exception:
            if conn:
                conn.close()
            raise


class HTTPSPool(HTTPPool):
    scheme = "https"
    ConnectionCls: type[HTTPSConnection] = HTTPSConnection  # type: ignore[assignment]

    def __init__(
        self,
        host: str,
        port: int | None = None,
        timeout: Timeout | float | _DefaultSentinel | None = DEFAULT_TIMEOUT,
        maxsize: int = 1,
        block: bool = False,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        _proxy: Url | None = None,
        _proxy_headers: typing.Mapping[str, str] | None = None,
        cert_reqs: int | str | None = None,
        ca_certs: str | None = None,
        ca_cert_dir: str | None = None,
        ca_cert_data: bytes | str | None = None,
        ssl_minimum_version: int | None = None,
        ssl_maximum_version: int | None = None,
        ssl_context: typing.Any | None = None,
        cert_file: str | None = None,
        key_file: str | None = None,
        key_password: str | None = None,
        assert_hostname: str | None | bool = None,
        assert_fingerprint: str | None = None,
        **conn_kw: typing.Any,
    ):
        super().__init__(
            host,
            port=port,
            timeout=timeout,
            maxsize=maxsize,
            block=block,
            headers=headers,
            retries=retries,
            _proxy=_proxy,
            _proxy_headers=_proxy_headers,
            **conn_kw,
        )
        self.cert_reqs = cert_reqs
        self.ca_certs = ca_certs
        self.ca_cert_dir = ca_cert_dir
        self.ca_cert_data = ca_cert_data
        self.ssl_minimum_version = ssl_minimum_version
        self.ssl_maximum_version = ssl_maximum_version
        self.ssl_context = ssl_context
        self.cert_file = cert_file
        self.key_file = key_file
        self.key_password = key_password
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint

    def _new_conn(self) -> HTTPSConnection:
        self.num_connections += 1
        log.debug(
            "Starting new HTTPS connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "443",
        )
        conn = self.ConnectionCls(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            cert_reqs=self.cert_reqs,
            ca_certs=self.ca_certs,
            ca_cert_dir=self.ca_cert_dir,
            ca_cert_data=self.ca_cert_data,
            ssl_minimum_version=self.ssl_minimum_version,
            ssl_maximum_version=self.ssl_maximum_version,
            ssl_context=self.ssl_context,
            cert_file=self.cert_file,
            key_file=self.key_file,
            key_password=self.key_password,
            assert_hostname=self.assert_hostname,
            assert_fingerprint=self.assert_fingerprint,
            **self.conn_kw,
        )
        return conn


def connection_from_url(url: str, **kw: typing.Any) -> HTTPPool | HTTPSPool:
    parsed = parse_url(url)
    scheme = (parsed.scheme or "http").lower()
    port = parsed.port
    host = parsed.host or "localhost"

    if scheme == "https":
        return HTTPSPool(host, port=port, **kw)
    return HTTPPool(host, port=port, **kw)
