from __future__ import annotations

import functools
import logging
import typing
from types import TracebackType
from urllib.parse import urljoin

from .connection import SCHEME_TO_PORT
from .connectionpool import HTTPPool, HTTPSPool
from .datastructures import HTTPHeaderDict, RecentlyUsedContainer
from .exceptions import (
    LocationValueError,
    MaxRetryError,
    ProxySchemeUnknown,
    URLSchemeUnknown,
)
from .request_methods import RequestMethods
from .retry import Retry
from .timeout import Timeout
from .url import Url, parse_url

if typing.TYPE_CHECKING:
    from .response import BaseHTTPResponse

log = logging.getLogger(__name__)

SSL_KEYWORDS = (
    "key_file",
    "cert_file",
    "cert_reqs",
    "ca_certs",
    "ca_cert_data",
    "ssl_minimum_version",
    "ssl_maximum_version",
    "ca_cert_dir",
    "ssl_context",
    "key_password",
    "assert_hostname",
    "assert_fingerprint",
)

pool_classes_by_scheme = {"http": HTTPPool, "https": HTTPSPool}


class PoolKey(typing.NamedTuple):
    key_scheme: str
    key_host: str
    key_port: int | None


def _pool_key(scheme: str, host: str, port: int | None) -> PoolKey:
    return PoolKey(
        key_scheme=scheme.lower(),
        key_host=host.lower(),
        key_port=port,
    )


class PoolManager(RequestMethods):
    proxy: Url | None = None

    def __init__(
        self,
        num_pools: int = 10,
        headers: typing.Mapping[str, str] | None = None,
        **connection_pool_kw: typing.Any,
    ) -> None:
        super().__init__(headers)
        self.connection_pool_kw = connection_pool_kw
        self.pools: RecentlyUsedContainer[PoolKey, HTTPPool] = RecentlyUsedContainer(
            num_pools
        )
        self.pool_classes_by_scheme = pool_classes_by_scheme

    def __enter__(self) -> PoolManager:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> typing.Literal[False]:
        self.clear()
        return False

    def _new_pool(
        self,
        scheme: str,
        host: str,
        port: int,
        request_context: dict[str, typing.Any] | None = None,
    ) -> HTTPPool:
        pool_cls: type[HTTPPool] = self.pool_classes_by_scheme[scheme]
        if request_context is None:
            request_context = self.connection_pool_kw.copy()
        else:
            request_context = request_context.copy()

        for key in ("scheme", "host", "port"):
            request_context.pop(key, None)

        if scheme == "http":
            for kw in SSL_KEYWORDS:
                request_context.pop(kw, None)

        return pool_cls(host, port=port, **request_context)

    def clear(self) -> None:
        self.pools.clear()

    def connection_from_host(
        self,
        host: str | None,
        port: int | None = None,
        scheme: str | None = "http",
        pool_kwargs: dict[str, typing.Any] | None = None,
    ) -> HTTPPool:
        if not host:
            raise LocationValueError("No host specified.")

        request_context = self._merge_pool_kwargs(pool_kwargs)
        request_context["scheme"] = scheme or "http"
        if not port:
            port = SCHEME_TO_PORT.get(request_context["scheme"].lower(), 80)
        request_context["port"] = port
        request_context["host"] = host

        return self._connection_from_context(request_context)

    def _connection_from_context(
        self, request_context: dict[str, typing.Any]
    ) -> HTTPPool:
        scheme = request_context["scheme"].lower()
        if scheme not in self.pool_classes_by_scheme:
            raise URLSchemeUnknown(scheme)

        pool_key = _pool_key(
            scheme, request_context["host"], request_context["port"]
        )

        with self.pools.lock:
            pool = self.pools.get(pool_key)
            if pool:
                return pool

            pool = self._new_pool(
                scheme,
                request_context["host"],
                request_context["port"],
                request_context=request_context,
            )
            self.pools[pool_key] = pool

        return pool

    def connection_from_url(
        self, url: str, pool_kwargs: dict[str, typing.Any] | None = None
    ) -> HTTPPool:
        u = parse_url(url)
        return self.connection_from_host(
            u.host, port=u.port, scheme=u.scheme, pool_kwargs=pool_kwargs
        )

    def _merge_pool_kwargs(
        self, override: dict[str, typing.Any] | None
    ) -> dict[str, typing.Any]:
        base_pool_kwargs = self.connection_pool_kw.copy()
        if override:
            for key, value in override.items():
                if value is None:
                    base_pool_kwargs.pop(key, None)
                else:
                    base_pool_kwargs[key] = value
        return base_pool_kwargs

    def urlopen(
        self, method: str, url: str, redirect: bool = True, **kw: typing.Any
    ) -> BaseHTTPResponse:
        u = parse_url(url)

        conn = self.connection_from_host(u.host, port=u.port, scheme=u.scheme)

        kw["redirect"] = False

        if "headers" not in kw:
            kw["headers"] = self.headers

        response = conn.urlopen(method, u.request_uri, **kw)

        redirect_location = redirect and response.get_redirect_location()
        if not redirect_location:
            return response

        redirect_location = urljoin(url, redirect_location)

        if response.status == 303:
            method = "GET"
            kw["body"] = None
            kw["headers"] = HTTPHeaderDict(kw["headers"])

        retries = kw.get("retries", response.retries)
        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect)

        try:
            retries = retries.increment(method, url, response=response, _pool=conn)
        except MaxRetryError:
            if retries.raise_on_redirect:
                response.drain_conn()
                raise
            return response

        kw["retries"] = retries
        kw["redirect"] = redirect

        log.info("Redirecting %s -> %s", url, redirect_location)

        response.drain_conn()
        return self.urlopen(method, redirect_location, **kw)


class ProxyManager(PoolManager):
    def __init__(
        self,
        proxy_url: str,
        num_pools: int = 10,
        headers: typing.Mapping[str, str] | None = None,
        proxy_headers: typing.Mapping[str, str] | None = None,
        **connection_pool_kw: typing.Any,
    ) -> None:
        proxy = parse_url(proxy_url)

        if proxy.scheme not in ("http", "https"):
            raise ProxySchemeUnknown(proxy.scheme)

        if not proxy.port:
            port = SCHEME_TO_PORT.get(proxy.scheme, 80)
            proxy = proxy._replace(port=port)

        self.proxy = proxy
        self.proxy_headers = proxy_headers or {}

        connection_pool_kw["_proxy"] = self.proxy
        connection_pool_kw["_proxy_headers"] = self.proxy_headers

        super().__init__(num_pools, headers, **connection_pool_kw)

    def connection_from_host(
        self,
        host: str | None,
        port: int | None = None,
        scheme: str | None = "http",
        pool_kwargs: dict[str, typing.Any] | None = None,
    ) -> HTTPPool:
        if scheme == "https":
            return super().connection_from_host(
                host, port, scheme, pool_kwargs=pool_kwargs
            )

        return super().connection_from_host(
            self.proxy.host, self.proxy.port, self.proxy.scheme, pool_kwargs=pool_kwargs
        )

    def _set_proxy_headers(
        self, url: str, headers: typing.Mapping[str, str] | None = None
    ) -> typing.Mapping[str, str]:
        headers_ = {"Accept": "*/*"}

        netloc = parse_url(url).netloc
        if netloc:
            headers_["Host"] = netloc

        if headers:
            headers_.update(headers)
        return headers_

    def urlopen(
        self, method: str, url: str, redirect: bool = True, **kw: typing.Any
    ) -> BaseHTTPResponse:
        u = parse_url(url)
        if u.scheme != "https":
            headers = kw.get("headers", self.headers)
            kw["headers"] = self._set_proxy_headers(url, headers)

        return super().urlopen(method, url, redirect=redirect, **kw)


def proxy_from_url(url: str, **kw: typing.Any) -> ProxyManager:
    return ProxyManager(proxy_url=url, **kw)
