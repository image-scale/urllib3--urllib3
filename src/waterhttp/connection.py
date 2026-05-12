from __future__ import annotations

import http.client
import socket
import ssl
import typing

from .exceptions import (
    ConnectTimeoutError,
    NewConnectionError,
    NameResolutionError,
)
from .timeout import Timeout, DEFAULT_TIMEOUT, _DefaultSentinel
from .ssl_helpers import create_ssl_context, assert_fingerprint

SCHEME_TO_PORT = {"http": 80, "https": 443}


def _create_connection(
    address: tuple[str, int],
    timeout: float | None = None,
    source_address: tuple[str, int] | None = None,
    socket_options: list[tuple[int, int, int | bytes]] | None = None,
) -> socket.socket:
    host, port = address
    err = None

    try:
        addrinfos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise OSError(f"Name resolution failed for {host}") from e

    for family, socktype, proto, canonname, sockaddr in addrinfos:
        sock = None
        try:
            sock = socket.socket(family, socktype, proto)
            if socket_options:
                for opt in socket_options:
                    sock.setsockopt(*opt)
            if timeout is not None:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as _e:
            err = _e
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    raise OSError(f"getaddrinfo returned empty list for {host}:{port}")


def is_connection_dropped(conn: HTTPConnection) -> bool:
    return not conn.is_connected


class HTTPConnection(http.client.HTTPConnection):
    default_port = 80
    default_socket_options: list[tuple[int, int, int | bytes]] = [
        (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    ]
    is_verified = False
    proxy_is_verified: bool | None = None

    def __init__(
        self,
        host: str,
        port: int | None = None,
        *,
        timeout: Timeout | float | _DefaultSentinel | None = DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
        blocksize: int = 16384,
        socket_options: list[tuple[int, int, int | bytes]] | None = default_socket_options,
        proxy: str | None = None,
        proxy_config: typing.Any | None = None,
    ) -> None:
        if isinstance(timeout, Timeout):
            self._timeout_obj = timeout
            connect_timeout = Timeout.resolve_default_timeout(timeout.connect_timeout)
        elif isinstance(timeout, _DefaultSentinel):
            self._timeout_obj = Timeout.from_float(None)
            connect_timeout = socket.getdefaulttimeout()
        elif timeout is None:
            self._timeout_obj = Timeout(total=None, connect=None, read=None)
            connect_timeout = None
        else:
            self._timeout_obj = Timeout.from_float(timeout)
            connect_timeout = timeout

        super().__init__(
            host,
            port=port,
            timeout=connect_timeout,
            source_address=source_address,
            blocksize=blocksize,
        )

        self.socket_options = socket_options
        self.proxy = proxy
        self.proxy_config = proxy_config

        self._tunnel_host: str | None = None
        self._tunnel_port: int | None = None
        self._tunnel_headers: dict[str, str] = {}
        self._tunnel_scheme: str = "http"

    @property
    def host(self) -> str:
        return self._dns_host

    @host.setter
    def host(self, value: str) -> None:
        self._dns_host = value

    @property
    def is_closed(self) -> bool:
        return self.sock is None

    @property
    def is_connected(self) -> bool:
        if self.sock is None:
            return False
        return True

    @property
    def has_connected_to_proxy(self) -> bool:
        return self.proxy is not None and self._tunnel_host is not None

    def set_tunnel(
        self,
        host: str,
        port: int | None = None,
        headers: dict[str, str] | None = None,
        scheme: str = "http",
    ) -> None:
        self._tunnel_host = host
        self._tunnel_port = port
        self._tunnel_headers = headers or {}
        self._tunnel_scheme = scheme
        super().set_tunnel(host, port=port, headers=headers)

    def connect(self) -> None:
        try:
            self.sock = _create_connection(
                (self._dns_host, self.port or self.default_port),
                timeout=self.timeout,
                source_address=self.source_address,
                socket_options=self.socket_options,
            )
        except socket.timeout as e:
            raise ConnectTimeoutError(
                f"Connection to {self.host} timed out. (connect timeout={self.timeout})"
            ) from e
        except socket.gaierror as e:
            raise NewConnectionError(
                self,
                f"Failed to resolve '{self.host}' ({e})"
            ) from e
        except OSError as e:
            raise NewConnectionError(
                self,
                f"Failed to establish a new connection: {e}"
            ) from e

        if self._tunnel_host:
            self._tunnel()  # type: ignore[attr-defined]


class HTTPSConnection(HTTPConnection):
    default_port = 443

    def __init__(
        self,
        host: str,
        port: int | None = None,
        *,
        timeout: Timeout | float | _DefaultSentinel | None = DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
        blocksize: int = 16384,
        socket_options: list[tuple[int, int, int | bytes]] | None = HTTPConnection.default_socket_options,
        proxy: str | None = None,
        proxy_config: typing.Any | None = None,
        cert_reqs: int | str | None = None,
        assert_hostname: str | None | bool = None,
        assert_fingerprint: str | None = None,
        ca_certs: str | None = None,
        ca_cert_dir: str | None = None,
        ca_cert_data: bytes | str | None = None,
        ssl_minimum_version: int | None = None,
        ssl_maximum_version: int | None = None,
        ssl_context: ssl.SSLContext | None = None,
        cert_file: str | None = None,
        key_file: str | None = None,
        key_password: str | None = None,
    ) -> None:
        super().__init__(
            host,
            port=port,
            timeout=timeout,
            source_address=source_address,
            blocksize=blocksize,
            socket_options=socket_options,
            proxy=proxy,
            proxy_config=proxy_config,
        )
        self.cert_reqs = cert_reqs
        self.assert_hostname = assert_hostname
        self.assert_fingerprint_value = assert_fingerprint
        self.ca_certs = ca_certs
        self.ca_cert_dir = ca_cert_dir
        self.ca_cert_data = ca_cert_data
        self.ssl_minimum_version = ssl_minimum_version
        self.ssl_maximum_version = ssl_maximum_version
        self.ssl_context = ssl_context
        self.cert_file = cert_file
        self.key_file = key_file
        self.key_password = key_password

    def connect(self) -> None:
        try:
            self.sock = _create_connection(
                (self._dns_host, self.port or self.default_port),
                timeout=self.timeout,
                source_address=self.source_address,
                socket_options=self.socket_options,
            )
        except socket.timeout as e:
            raise ConnectTimeoutError(
                f"Connection to {self.host} timed out. (connect timeout={self.timeout})"
            ) from e
        except socket.gaierror as e:
            raise NewConnectionError(
                self,
                f"Failed to resolve '{self.host}' ({e})"
            ) from e
        except OSError as e:
            raise NewConnectionError(
                self,
                f"Failed to establish a new connection: {e}"
            ) from e

        if self._tunnel_host:
            self._tunnel()  # type: ignore[attr-defined]

        server_hostname = self._tunnel_host or self.host

        ctx = self.ssl_context
        if ctx is None:
            from .ssl_helpers import resolve_cert_reqs
            cert_reqs_val = resolve_cert_reqs(self.cert_reqs)
            ctx = create_ssl_context(
                ssl_minimum_version=self.ssl_minimum_version,
                ssl_maximum_version=self.ssl_maximum_version,
                cert_reqs=cert_reqs_val,
            )

        if self.cert_file:
            ctx.load_cert_chain(self.cert_file, self.key_file, self.key_password)

        if self.ca_certs or self.ca_cert_dir or self.ca_cert_data:
            ctx.load_verify_locations(self.ca_certs, self.ca_cert_dir, self.ca_cert_data)
        elif ctx.verify_mode != ssl.CERT_NONE:
            ctx.load_default_certs()

        if self.assert_fingerprint_value:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        hostname_to_check = server_hostname
        if self.assert_hostname is not None:
            if isinstance(self.assert_hostname, str):
                hostname_to_check = self.assert_hostname
            elif self.assert_hostname is False:
                ctx.check_hostname = False

        self.sock = ctx.wrap_socket(self.sock, server_hostname=hostname_to_check)

        if self.assert_fingerprint_value:
            cert_binary = self.sock.getpeercert(binary_form=True)
            assert_fingerprint(cert_binary, self.assert_fingerprint_value)

        self.is_verified = ctx.verify_mode == ssl.CERT_REQUIRED
