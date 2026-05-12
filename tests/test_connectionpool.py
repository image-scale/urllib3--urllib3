from __future__ import annotations

import queue
import threading
from unittest.mock import Mock

import pytest

from waterhttp.connectionpool import (
    BasePool,
    HTTPPool,
    HTTPSPool,
    connection_from_url,
)
from waterhttp.connection import HTTPConnection, HTTPSConnection
from waterhttp.exceptions import (
    ClosedPoolError,
    EmptyPoolError,
    FullPoolError,
    LocationValueError,
)
from waterhttp.timeout import Timeout


class TestBasePool:
    def test_str(self):
        pool = BasePool("example.com", port=80)
        assert "BasePool" in str(pool)
        assert "example.com" in str(pool)

    def test_no_host_raises(self):
        with pytest.raises(LocationValueError):
            BasePool("")

    def test_context_manager(self):
        with BasePool("example.com") as pool:
            assert pool.host == "example.com"

    def test_close_noop(self):
        pool = BasePool("example.com")
        pool.close()

    def test_exit_returns_false(self):
        pool = BasePool("example.com")
        assert pool.__exit__(None, None, None) is False


class TestHTTPPool:
    def test_default_maxsize(self):
        pool = HTTPPool("example.com")
        assert pool.pool is not None
        assert pool.pool.maxsize == 1

    def test_custom_maxsize(self):
        pool = HTTPPool("example.com", maxsize=5)
        assert pool.pool is not None
        assert pool.pool.maxsize == 5

    def test_scheme(self):
        pool = HTTPPool("example.com")
        assert pool.scheme == "http"

    def test_host_port(self):
        pool = HTTPPool("example.com", port=8080)
        assert pool.host == "example.com"
        assert pool.port == 8080

    def test_default_port_none(self):
        pool = HTTPPool("example.com")
        assert pool.port is None

    def test_num_connections_starts_zero(self):
        pool = HTTPPool("example.com")
        assert pool.num_connections == 0

    def test_num_requests_starts_zero(self):
        pool = HTTPPool("example.com")
        assert pool.num_requests == 0

    def test_new_conn_increments_count(self):
        pool = HTTPPool("example.com")
        conn = pool._new_conn()
        assert pool.num_connections == 1
        assert isinstance(conn, HTTPConnection)

    def test_new_conn_sets_host(self):
        pool = HTTPPool("example.com", port=9090)
        conn = pool._new_conn()
        assert conn.host == "example.com"
        assert conn.port == 9090

    def test_get_conn_creates_new_when_empty(self):
        pool = HTTPPool("example.com")
        conn = pool._get_conn()
        assert isinstance(conn, HTTPConnection)
        assert pool.num_connections == 1

    def test_get_conn_reuses_returned(self):
        pool = HTTPPool("example.com")
        conn1 = pool._get_conn()
        conn1.sock = Mock()
        pool._return_conn(conn1)
        conn2 = pool._get_conn()
        assert conn2 is conn1
        assert pool.num_connections == 1

    def test_return_conn_then_get(self):
        pool = HTTPPool("example.com", maxsize=2)
        conn = pool._new_conn()
        conn.sock = Mock()
        pool.pool.get_nowait()
        pool._return_conn(conn)
        got = pool._get_conn()
        assert got is conn

    def test_lifo_order(self):
        pool = HTTPPool("example.com", maxsize=3)
        pool._get_conn()
        pool._get_conn()
        pool._get_conn()
        c1 = pool._new_conn()
        c1.sock = Mock()
        c2 = pool._new_conn()
        c2.sock = Mock()
        pool._return_conn(c1)
        pool._return_conn(c2)
        got = pool._get_conn()
        assert got is c2

    def test_pool_is_lifo_queue(self):
        pool = HTTPPool("example.com")
        assert isinstance(pool.pool, queue.LifoQueue)

    def test_pool_filled_with_nones(self):
        pool = HTTPPool("example.com", maxsize=3)
        items = []
        for _ in range(3):
            items.append(pool.pool.get_nowait())
        assert items == [None, None, None]

    def test_get_conn_on_closed_pool_raises(self):
        pool = HTTPPool("example.com")
        pool.close()
        with pytest.raises(ClosedPoolError):
            pool._get_conn()

    def test_return_conn_to_closed_pool_closes_conn(self):
        pool = HTTPPool("example.com")
        conn = pool._new_conn()
        pool.close()
        pool._return_conn(conn)

    def test_return_conn_to_full_pool_nonblocking(self):
        pool = HTTPPool("example.com", maxsize=1, block=False)
        conn1 = pool._new_conn()
        conn2 = pool._new_conn()
        pool._return_conn(conn1)
        pool._return_conn(conn2)

    def test_return_conn_to_full_pool_blocking_raises(self):
        pool = HTTPPool("example.com", maxsize=1, block=True)
        pool._get_conn()
        c1 = pool._new_conn()
        pool._return_conn(c1)
        c2 = pool._new_conn()
        with pytest.raises(FullPoolError):
            pool._return_conn(c2)

    def test_close_empties_pool(self):
        pool = HTTPPool("example.com", maxsize=3)
        pool.close()
        assert pool.pool is None

    def test_close_idempotent(self):
        pool = HTTPPool("example.com")
        pool.close()
        pool.close()

    def test_context_manager_closes(self):
        with HTTPPool("example.com") as pool:
            pass
        assert pool.pool is None

    def test_block_false_creates_new(self):
        pool = HTTPPool("example.com", maxsize=1, block=False)
        c1 = pool._get_conn()
        c2 = pool._get_conn()
        assert pool.num_connections == 2

    def test_block_true_empty_pool_raises(self):
        pool = HTTPPool("example.com", maxsize=1, block=True)
        pool._get_conn()
        with pytest.raises(EmptyPoolError):
            pool._get_conn(timeout=0.01)

    def test_timeout_as_timeout_obj(self):
        t = Timeout(connect=5, read=10)
        pool = HTTPPool("example.com", timeout=t)
        assert pool.timeout.connect_timeout == 5
        assert pool.timeout.read_timeout == 10

    def test_timeout_as_float(self):
        pool = HTTPPool("example.com", timeout=5.0)
        assert isinstance(pool.timeout, Timeout)

    def test_retries_default(self):
        from waterhttp.retry import Retry
        pool = HTTPPool("example.com")
        assert isinstance(pool.retries, Retry)

    def test_proxy_attrs(self):
        from waterhttp.url import Url
        proxy = Url(scheme="http", host="proxy.com", port=3128)
        pool = HTTPPool("example.com", _proxy=proxy, _proxy_headers={"Proxy-Auth": "token"})
        assert pool.proxy == proxy
        assert pool.proxy_headers == {"Proxy-Auth": "token"}

    def test_proxy_headers_default_empty(self):
        pool = HTTPPool("example.com")
        assert pool.proxy_headers == {}

    def test_conn_kw_passed(self):
        pool = HTTPPool("example.com", source_address=("0.0.0.0", 0))
        assert pool.conn_kw == {"source_address": ("0.0.0.0", 0)}

    def test_ipv6_host_normalization(self):
        pool = HTTPPool("[::1]")
        assert pool.host == "[::1]"

    def test_no_host_raises(self):
        with pytest.raises(LocationValueError):
            HTTPPool("")


class TestIsSameHost:
    def test_same_host(self):
        pool = HTTPPool("example.com")
        assert pool.is_same_host("http://example.com/path") is True

    def test_different_host(self):
        pool = HTTPPool("example.com")
        assert pool.is_same_host("http://other.com/path") is False

    def test_same_host_with_port(self):
        pool = HTTPPool("example.com", port=8080)
        assert pool.is_same_host("http://example.com:8080/path") is True

    def test_different_port(self):
        pool = HTTPPool("example.com", port=8080)
        assert pool.is_same_host("http://example.com:9090/path") is False

    def test_https_scheme_mismatch(self):
        pool = HTTPPool("example.com")
        assert pool.is_same_host("https://example.com/path") is False

    def test_no_port_in_url_matches_no_port_pool(self):
        pool = HTTPPool("example.com")
        assert pool.is_same_host("http://example.com/path") is True

    def test_pool_port_matches_scheme_default(self):
        pool = HTTPPool("example.com", port=80)
        assert pool.is_same_host("http://example.com/path") is True

    def test_dropped_conn_replaced(self):
        pool = HTTPPool("example.com")
        conn = pool._get_conn()
        pool._return_conn(conn)
        got = pool._get_conn()
        assert got is not conn
        assert pool.num_connections == 2

    def test_ipv6(self):
        pool = HTTPPool("[::1]")
        assert pool.is_same_host("http://[::1]/path") is True


class TestHTTPSPool:
    def test_scheme(self):
        pool = HTTPSPool("example.com")
        assert pool.scheme == "https"

    def test_connection_cls(self):
        pool = HTTPSPool("example.com")
        assert pool.ConnectionCls is HTTPSConnection

    def test_ssl_params_stored(self):
        pool = HTTPSPool(
            "example.com",
            cert_reqs="REQUIRED",
            ca_certs="/path/to/ca",
            cert_file="/path/to/cert",
            key_file="/path/to/key",
            key_password="secret",
            assert_hostname="example.com",
            assert_fingerprint="AA:BB:CC",
        )
        assert pool.cert_reqs == "REQUIRED"
        assert pool.ca_certs == "/path/to/ca"
        assert pool.cert_file == "/path/to/cert"
        assert pool.key_file == "/path/to/key"
        assert pool.key_password == "secret"
        assert pool.assert_hostname == "example.com"
        assert pool.assert_fingerprint == "AA:BB:CC"

    def test_new_conn_returns_https(self):
        pool = HTTPSPool("example.com")
        conn = pool._new_conn()
        assert isinstance(conn, HTTPSConnection)

    def test_new_conn_passes_ssl_params(self):
        pool = HTTPSPool(
            "example.com",
            ca_certs="/ca",
            cert_file="/cert",
            key_file="/key",
        )
        conn = pool._new_conn()
        assert conn.ca_certs == "/ca"
        assert conn.cert_file == "/cert"
        assert conn.key_file == "/key"

    def test_ssl_context_passthrough(self):
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        pool = HTTPSPool("example.com", ssl_context=ctx)
        conn = pool._new_conn()
        assert conn.ssl_context is ctx

    def test_inherits_pool_behavior(self):
        pool = HTTPSPool("example.com", maxsize=3)
        assert pool.pool is not None
        assert pool.pool.maxsize == 3

    def test_is_same_host_https(self):
        pool = HTTPSPool("example.com")
        assert pool.is_same_host("https://example.com/path") is True
        assert pool.is_same_host("http://example.com/path") is False


class TestConnectionFromUrl:
    def test_http_url(self):
        pool = connection_from_url("http://example.com")
        assert isinstance(pool, HTTPPool)
        assert not isinstance(pool, HTTPSPool)
        assert pool.host == "example.com"

    def test_https_url(self):
        pool = connection_from_url("https://example.com")
        assert isinstance(pool, HTTPSPool)
        assert pool.host == "example.com"

    def test_with_port(self):
        pool = connection_from_url("http://example.com:8080")
        assert pool.port == 8080

    def test_default_host(self):
        pool = connection_from_url("/path")
        assert pool.host == "localhost"

    def test_passes_kwargs(self):
        pool = connection_from_url("http://example.com", maxsize=5)
        assert pool.pool is not None
        assert pool.pool.maxsize == 5
