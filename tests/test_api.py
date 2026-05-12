from __future__ import annotations

import logging

import pytest

import waterhttp
from waterhttp.connectionpool import HTTPPool, HTTPSPool, connection_from_url
from waterhttp.datastructures import HTTPHeaderDict
from waterhttp.exceptions import (
    HTTPError,
    HTTPWarning,
    LocationParseError,
    LocationValueError,
)
from waterhttp.multipart import encode_multipart_formdata
from waterhttp.poolmanager import PoolManager, ProxyManager, proxy_from_url
from waterhttp.request_helpers import make_headers
from waterhttp.response import BaseHTTPResponse, WaterHTTPResponse
from waterhttp.retry import Retry
from waterhttp.timeout import Timeout
from waterhttp.url import Url, parse_url


class TestPublicExports:
    def test_httppool(self):
        assert waterhttp.HTTPPool is HTTPPool

    def test_httpspool(self):
        assert waterhttp.HTTPSPool is HTTPSPool

    def test_httpheaderdict(self):
        assert waterhttp.HTTPHeaderDict is HTTPHeaderDict

    def test_poolmanager(self):
        assert waterhttp.PoolManager is PoolManager

    def test_proxymanager(self):
        assert waterhttp.ProxyManager is ProxyManager

    def test_waterhttpresponse(self):
        assert waterhttp.WaterHTTPResponse is WaterHTTPResponse

    def test_basehttpresponse(self):
        assert waterhttp.BaseHTTPResponse is BaseHTTPResponse

    def test_retry(self):
        assert waterhttp.Retry is Retry

    def test_timeout(self):
        assert waterhttp.Timeout is Timeout

    def test_url(self):
        assert waterhttp.Url is Url

    def test_parse_url(self):
        assert waterhttp.parse_url is parse_url

    def test_connection_from_url(self):
        assert waterhttp.connection_from_url is connection_from_url

    def test_proxy_from_url(self):
        assert waterhttp.proxy_from_url is proxy_from_url

    def test_make_headers(self):
        assert waterhttp.make_headers is make_headers

    def test_encode_multipart_formdata(self):
        assert waterhttp.encode_multipart_formdata is encode_multipart_formdata

    def test_request_function(self):
        assert callable(waterhttp.request)

    def test_add_stderr_logger(self):
        assert callable(waterhttp.add_stderr_logger)

    def test_disable_warnings(self):
        assert callable(waterhttp.disable_warnings)


class TestAllAttribute:
    def test_all_contains_key_names(self):
        for name in [
            "HTTPPool",
            "HTTPSPool",
            "HTTPHeaderDict",
            "PoolManager",
            "ProxyManager",
            "WaterHTTPResponse",
            "BaseHTTPResponse",
            "Retry",
            "Timeout",
            "request",
            "connection_from_url",
            "proxy_from_url",
            "make_headers",
            "encode_multipart_formdata",
            "parse_url",
            "add_stderr_logger",
            "disable_warnings",
        ]:
            assert name in waterhttp.__all__, f"{name} not in __all__"


class TestExceptionExports:
    def test_httperror(self):
        assert waterhttp.HTTPError is HTTPError

    def test_httpwarning(self):
        assert waterhttp.HTTPWarning is HTTPWarning

    def test_locationparseerror(self):
        assert waterhttp.LocationParseError is LocationParseError

    def test_locationvalueerror(self):
        assert waterhttp.LocationValueError is LocationValueError


class TestAddStderrLogger:
    def test_returns_handler(self):
        handler = waterhttp.add_stderr_logger(logging.WARNING)
        assert isinstance(handler, logging.StreamHandler)
        logger = logging.getLogger("waterhttp")
        logger.removeHandler(handler)

    def test_sets_level(self):
        handler = waterhttp.add_stderr_logger(logging.ERROR)
        logger = logging.getLogger("waterhttp")
        assert logger.level == logging.ERROR
        logger.removeHandler(handler)
        logger.setLevel(logging.WARNING)


class TestDisableWarnings:
    def test_suppresses_warnings(self):
        import warnings
        waterhttp.disable_warnings(HTTPWarning)
        with warnings.catch_warnings(record=True) as w:
            warnings.warn("test", HTTPWarning)
        waterhttp.disable_warnings.__wrapped__ = None  # noqa


class TestRequestFunction:
    def test_request_is_callable(self):
        assert callable(waterhttp.request)

    def test_default_pool_exists(self):
        assert isinstance(waterhttp._DEFAULT_POOL, PoolManager)


class TestConnectionFromUrl:
    def test_http(self):
        pool = waterhttp.connection_from_url("http://example.com")
        assert isinstance(pool, HTTPPool)
        assert pool.host == "example.com"

    def test_https(self):
        pool = waterhttp.connection_from_url("https://example.com")
        assert isinstance(pool, HTTPSPool)


class TestMakeHeaders:
    def test_user_agent(self):
        h = waterhttp.make_headers(user_agent="MyApp/1.0")
        assert h["user-agent"] == "MyApp/1.0"

    def test_keep_alive(self):
        h = waterhttp.make_headers(keep_alive=True)
        assert "connection" in h


class TestEncodeMultipart:
    def test_basic(self):
        body, content_type = waterhttp.encode_multipart_formdata(
            {"field": "value"}
        )
        assert b"field" in body
        assert b"value" in body
        assert "multipart/form-data" in content_type
