from __future__ import annotations

import typing

import pytest

from waterhttp.poolmanager import (
    PoolManager,
    ProxyManager,
    proxy_from_url,
    PoolKey,
    _pool_key,
)
from waterhttp.connectionpool import HTTPPool, HTTPSPool
from waterhttp.exceptions import (
    LocationValueError,
    ProxySchemeUnknown,
    URLSchemeUnknown,
)
from waterhttp.url import Url


class TestPoolKey:
    def test_basic(self):
        key = _pool_key("http", "example.com", 80)
        assert key.key_scheme == "http"
        assert key.key_host == "example.com"
        assert key.key_port == 80

    def test_case_insensitive(self):
        k1 = _pool_key("HTTP", "Example.COM", 80)
        k2 = _pool_key("http", "example.com", 80)
        assert k1 == k2

    def test_different_ports(self):
        k1 = _pool_key("http", "example.com", 80)
        k2 = _pool_key("http", "example.com", 8080)
        assert k1 != k2

    def test_different_schemes(self):
        k1 = _pool_key("http", "example.com", 80)
        k2 = _pool_key("https", "example.com", 80)
        assert k1 != k2


class TestPoolManager:
    def test_same_url_same_pool(self):
        p = PoolManager(10)
        c1 = p.connection_from_url("http://example.com/foo")
        c2 = p.connection_from_url("http://example.com/bar")
        assert c1 is c2

    def test_different_hosts_different_pools(self):
        p = PoolManager(10)
        c1 = p.connection_from_url("http://example.com")
        c2 = p.connection_from_url("http://other.com")
        assert c1 is not c2

    def test_different_schemes_different_pools(self):
        p = PoolManager(10)
        c1 = p.connection_from_url("http://example.com")
        c2 = p.connection_from_url("https://example.com")
        assert c1 is not c2

    def test_different_ports_different_pools(self):
        p = PoolManager(10)
        c1 = p.connection_from_url("http://example.com:8080")
        c2 = p.connection_from_url("http://example.com:9090")
        assert c1 is not c2

    def test_http_pool_type(self):
        p = PoolManager()
        pool = p.connection_from_url("http://example.com")
        assert isinstance(pool, HTTPPool)
        assert not isinstance(pool, HTTPSPool)

    def test_https_pool_type(self):
        p = PoolManager()
        pool = p.connection_from_url("https://example.com")
        assert isinstance(pool, HTTPSPool)

    def test_many_urls(self):
        urls = [
            "http://localhost:8081/foo",
            "http://www.google.com/mail",
            "http://localhost:8081/bar",
            "https://www.google.com/",
            "https://www.google.com/mail",
            "http://yahoo.com",
            "http://bing.com",
            "http://yahoo.com/",
        ]
        p = PoolManager(10)
        pools = set()
        for url in urls:
            pools.add(id(p.connection_from_url(url)))
        assert len(pools) == 5

    def test_manager_clear(self):
        p = PoolManager(5)
        p.connection_from_url("http://google.com")
        assert len(p.pools) == 1
        p.clear()
        assert len(p.pools) == 0

    def test_nohost_raises(self):
        p = PoolManager(5)
        with pytest.raises(LocationValueError):
            p.connection_from_host(None)

    def test_empty_host_raises(self):
        p = PoolManager(5)
        with pytest.raises(LocationValueError):
            p.connection_from_host("")

    def test_context_manager(self):
        with PoolManager(1) as p:
            p.connection_from_url("http://google.com")
            assert len(p.pools) == 1
        assert len(p.pools) == 0

    def test_num_pools_lru_eviction(self):
        p = PoolManager(2)
        p.connection_from_url("http://a.com")
        p.connection_from_url("http://b.com")
        assert len(p.pools) == 2
        p.connection_from_url("http://c.com")
        assert len(p.pools) == 2

    def test_connection_from_host_default_scheme(self):
        p = PoolManager()
        pool = p.connection_from_host("example.com")
        assert pool.scheme == "http"

    def test_connection_from_host_with_port(self):
        p = PoolManager()
        pool = p.connection_from_host("example.com", port=8080, scheme="http")
        assert pool.port == 8080

    def test_connection_from_host_default_port(self):
        p = PoolManager()
        pool = p.connection_from_host("example.com", scheme="http")
        assert pool.port is not None

    def test_connection_pool_kw_forwarded(self):
        p = PoolManager(maxsize=5)
        pool = p.connection_from_url("http://example.com")
        assert pool.pool is not None
        assert pool.pool.maxsize == 5

    def test_merge_pool_kwargs(self):
        p = PoolManager(maxsize=5, block=True)
        merged = p._merge_pool_kwargs({"maxsize": 10})
        assert merged["maxsize"] == 10
        assert merged["block"] is True

    def test_merge_pool_kwargs_remove_none(self):
        p = PoolManager(maxsize=5, block=True)
        merged = p._merge_pool_kwargs({"block": None})
        assert "block" not in merged
        assert merged["maxsize"] == 5

    def test_merge_pool_kwargs_none_override(self):
        p = PoolManager(maxsize=5)
        merged = p._merge_pool_kwargs(None)
        assert merged["maxsize"] == 5

    def test_connection_from_url_pool_kwargs(self):
        p = PoolManager()
        pool = p.connection_from_url(
            "http://example.com", pool_kwargs={"maxsize": 3}
        )
        assert pool.pool is not None
        assert pool.pool.maxsize == 3

    def test_unknown_scheme_raises(self):
        p = PoolManager()
        with pytest.raises(URLSchemeUnknown):
            p.connection_from_url("ftp://example.com")

    def test_ssl_keywords_stripped_for_http(self):
        p = PoolManager(ca_certs="/path/to/ca")
        pool = p.connection_from_url("http://example.com")
        assert isinstance(pool, HTTPPool)
        assert not isinstance(pool, HTTPSPool)

    def test_ssl_keywords_kept_for_https(self):
        p = PoolManager(ca_certs="/path/to/ca")
        pool = p.connection_from_url("https://example.com")
        assert isinstance(pool, HTTPSPool)
        assert pool.ca_certs == "/path/to/ca"


class TestProxyManager:
    def test_basic_creation(self):
        pm = ProxyManager("http://proxy.com:3128")
        assert pm.proxy.host == "proxy.com"
        assert pm.proxy.port == 3128
        assert pm.proxy.scheme == "http"

    def test_default_port_http(self):
        pm = ProxyManager("http://proxy.com")
        assert pm.proxy.port == 80

    def test_default_port_https(self):
        pm = ProxyManager("https://proxy.com")
        assert pm.proxy.port == 443

    def test_invalid_scheme_raises(self):
        with pytest.raises(ProxySchemeUnknown):
            ProxyManager("ftp://proxy.com")

    def test_proxy_headers(self):
        pm = ProxyManager(
            "http://proxy.com",
            proxy_headers={"Proxy-Auth": "token"},
        )
        assert pm.proxy_headers == {"Proxy-Auth": "token"}

    def test_proxy_headers_default_empty(self):
        pm = ProxyManager("http://proxy.com")
        assert pm.proxy_headers == {}

    def test_http_routes_through_proxy(self):
        pm = ProxyManager("http://proxy.com:3128")
        pool = pm.connection_from_url("http://example.com")
        assert pool.host == "proxy.com"
        assert pool.port == 3128

    def test_https_direct_pool(self):
        pm = ProxyManager("http://proxy.com:3128")
        pool = pm.connection_from_url("https://example.com")
        assert pool.host == "example.com"

    def test_set_proxy_headers(self):
        pm = ProxyManager("http://proxy.com:3128")
        headers = pm._set_proxy_headers(
            "http://example.com/path", {"X-Custom": "val"}
        )
        assert headers["Accept"] == "*/*"
        assert headers["Host"] == "example.com"
        assert headers["X-Custom"] == "val"

    def test_context_manager(self):
        with ProxyManager("http://proxy.com") as pm:
            pool = pm.connection_from_url("http://example.com")
            assert len(pm.pools) == 1
        assert len(pm.pools) == 0


class TestProxyFromUrl:
    def test_returns_proxy_manager(self):
        pm = proxy_from_url("http://proxy.com:3128")
        assert isinstance(pm, ProxyManager)
        assert pm.proxy.host == "proxy.com"
        assert pm.proxy.port == 3128

    def test_kwargs_forwarded(self):
        pm = proxy_from_url("http://proxy.com:3128", num_pools=5)
        assert pm.pools._maxsize == 5
