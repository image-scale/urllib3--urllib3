from __future__ import annotations

import io

import pytest

from waterhttp.request_helpers import (
    make_headers,
    body_to_chunks,
    rewind_body,
    ACCEPT_ENCODING,
)
from waterhttp.request_methods import RequestMethods
from waterhttp.exceptions import UnrewindableBodyError


class TestMakeHeaders:
    def test_keep_alive(self):
        h = make_headers(keep_alive=True)
        assert h["connection"] == "keep-alive"

    def test_accept_encoding_true(self):
        h = make_headers(accept_encoding=True)
        assert "gzip" in h["accept-encoding"]
        assert "deflate" in h["accept-encoding"]

    def test_accept_encoding_list(self):
        h = make_headers(accept_encoding=["gzip", "br"])
        assert h["accept-encoding"] == "gzip,br"

    def test_accept_encoding_string(self):
        h = make_headers(accept_encoding="identity")
        assert h["accept-encoding"] == "identity"

    def test_user_agent(self):
        h = make_headers(user_agent="Bot/1.0")
        assert h["user-agent"] == "Bot/1.0"

    def test_basic_auth(self):
        h = make_headers(basic_auth="user:pass")
        assert h["authorization"] == "Basic dXNlcjpwYXNz"

    def test_proxy_basic_auth(self):
        h = make_headers(proxy_basic_auth="user:pass")
        assert h["proxy-authorization"] == "Basic dXNlcjpwYXNz"

    def test_disable_cache(self):
        h = make_headers(disable_cache=True)
        assert h["cache-control"] == "no-cache"

    def test_empty(self):
        h = make_headers()
        assert h == {}

    def test_multiple_options(self):
        h = make_headers(keep_alive=True, user_agent="Bot/1.0", disable_cache=True)
        assert h["connection"] == "keep-alive"
        assert h["user-agent"] == "Bot/1.0"
        assert h["cache-control"] == "no-cache"


class TestBodyToChunks:
    def test_none_body_post(self):
        result = body_to_chunks(None, "POST", 8192)
        assert result.chunks is None
        assert result.content_length == 0

    def test_none_body_get(self):
        result = body_to_chunks(None, "GET", 8192)
        assert result.chunks is None
        assert result.content_length is None

    def test_bytes_body(self):
        result = body_to_chunks(b"hello", "POST", 8192)
        chunks = list(result.chunks)
        assert chunks == [b"hello"]
        assert result.content_length == 5

    def test_string_body(self):
        result = body_to_chunks("hello", "POST", 8192)
        chunks = list(result.chunks)
        assert chunks == [b"hello"]
        assert result.content_length == 5

    def test_file_body(self):
        body = io.BytesIO(b"file content")
        result = body_to_chunks(body, "POST", 4)
        assert result.content_length is None
        chunks = list(result.chunks)
        assert b"".join(chunks) == b"file content"

    def test_text_file_body(self):
        body = io.StringIO("text content")
        result = body_to_chunks(body, "POST", 4)
        assert result.content_length is None
        chunks = list(result.chunks)
        assert b"".join(chunks) == b"text content"

    def test_iterable_body(self):
        body = [b"chunk1", b"chunk2"]
        result = body_to_chunks(body, "POST", 8192)
        assert result.content_length is None
        chunks = list(result.chunks)
        assert chunks == [b"chunk1", b"chunk2"]

    def test_memoryview_body(self):
        data = b"memory data"
        result = body_to_chunks(data, "POST", 8192)
        assert result.content_length == len(data)

    def test_invalid_body_raises(self):
        with pytest.raises(TypeError, match="bytes-like"):
            body_to_chunks(12345, "POST", 8192)


class TestRewindBody:
    def test_rewind_seekable(self):
        body = io.BytesIO(b"hello")
        body.read(3)
        rewind_body(body, 0)
        assert body.read() == b"hello"

    def test_rewind_non_seekable_raises(self):
        with pytest.raises(ValueError):
            rewind_body(object(), "not_an_int")  # type: ignore[arg-type]


class _MockUrlOpen(RequestMethods):
    def __init__(self):
        super().__init__()
        self.calls = []

    def urlopen(self, method, url, body=None, headers=None, **kw):
        self.calls.append({
            "method": method,
            "url": url,
            "body": body,
            "headers": headers,
        })
        return None  # type: ignore[return-value]


class TestRequestMethods:
    def test_get_routes_to_url_encoding(self):
        m = _MockUrlOpen()
        m.request("GET", "/path", fields={"key": "value"})
        assert len(m.calls) == 1
        assert "key=value" in m.calls[0]["url"]
        assert m.calls[0]["body"] is None

    def test_post_routes_to_body_encoding(self):
        m = _MockUrlOpen()
        m.request("POST", "/path", fields={"key": "value"})
        assert len(m.calls) == 1
        assert m.calls[0]["url"] == "/path"
        assert m.calls[0]["body"] is not None

    def test_json_encoding(self):
        m = _MockUrlOpen()
        m.request("POST", "/path", json={"key": "value"})
        call = m.calls[0]
        assert call["body"] == b'{"key": "value"}'
        assert "Content-Type" in call["headers"] or "content-type" in call["headers"]

    def test_json_and_body_raises(self):
        m = _MockUrlOpen()
        with pytest.raises(TypeError, match="mutually exclusive"):
            m.request("POST", "/path", body=b"data", json={"key": "value"})

    def test_convenience_methods(self):
        m = _MockUrlOpen()
        m.get("/a")
        m.post("/b")
        m.put("/c")
        m.patch("/d")
        m.delete("/e")
        m.head("/f")
        m.options("/g")
        methods = [c["method"] for c in m.calls]
        assert methods == ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

    def test_head_routes_to_url_encoding(self):
        m = _MockUrlOpen()
        m.request("HEAD", "/path", fields={"key": "value"})
        assert "key=value" in m.calls[0]["url"]

    def test_delete_routes_to_url_encoding(self):
        m = _MockUrlOpen()
        m.request("DELETE", "/path", fields={"key": "value"})
        assert "key=value" in m.calls[0]["url"]

    def test_put_routes_to_body_encoding(self):
        m = _MockUrlOpen()
        m.request("PUT", "/path", fields={"key": "value"})
        assert m.calls[0]["body"] is not None

    def test_post_no_multipart(self):
        m = _MockUrlOpen()
        m.request_encode_body("POST", "/path", fields={"key": "value"}, encode_multipart=False)
        call = m.calls[0]
        assert call["body"] == b"key=value"

    def test_post_with_multipart(self):
        m = _MockUrlOpen()
        m.request_encode_body("POST", "/path", fields={"key": "value"})
        call = m.calls[0]
        assert b"key" in call["body"]
        assert b"value" in call["body"]

    def test_post_json_sets_content_type(self):
        m = _MockUrlOpen()
        m.request("POST", "/path", json={"a": 1})
        headers = m.calls[0]["headers"]
        ct = headers.get("Content-Type", headers.get("content-type", ""))
        assert ct == "application/json"
