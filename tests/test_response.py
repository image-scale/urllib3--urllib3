from __future__ import annotations

import gzip
import sys
import typing
import zlib
from io import BytesIO

import pytest

from waterhttp.response import (
    BaseHTTPResponse,
    BytesQueueBuffer,
    WaterHTTPResponse,
    DeflateDecoder,
    GzipDecoder,
    _get_decoder,
    is_fp_closed,
    brotli,
    HAS_ZSTD,
    CONTENT_DECODERS,
)
from waterhttp.exceptions import (
    DecodeError,
    IncompleteRead,
    InvalidHeader,
    ResponseNotChunked,
)
from waterhttp.retry import Retry


def zstd_compress(data: bytes) -> bytes:
    if sys.version_info >= (3, 14):
        from compression import zstd
    else:
        from backports import zstd
    return zstd.compress(data)


def deflate2_compress(data: bytes) -> bytes:
    compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
    return compressor.compress(data) + compressor.flush()


class TestBytesQueueBuffer:
    def test_empty(self):
        buf = BytesQueueBuffer()
        assert len(buf) == 0

    def test_put_and_get(self):
        buf = BytesQueueBuffer()
        buf.put(b"hello")
        assert len(buf) == 5
        assert buf.get(3) == b"hel"
        assert len(buf) == 2
        assert buf.get(2) == b"lo"

    def test_get_zero(self):
        buf = BytesQueueBuffer()
        assert buf.get(0) == b""

    def test_get_empty_raises(self):
        buf = BytesQueueBuffer()
        with pytest.raises(RuntimeError, match="buffer is empty"):
            buf.get(1)

    def test_get_negative_raises(self):
        buf = BytesQueueBuffer()
        buf.put(b"data")
        with pytest.raises(ValueError, match="n should be > 0"):
            buf.get(-1)

    def test_multiple_chunks(self):
        buf = BytesQueueBuffer()
        buf.put(b"foo")
        buf.put(b"bar")
        buf.put(b"baz")
        assert len(buf) == 9
        assert buf.get(4) == b"foob"
        assert buf.get(5) == b"arbaz"

    def test_read_more_than_available(self):
        buf = BytesQueueBuffer()
        buf.put(b"abc")
        assert buf.get(100) == b"abc"

    def test_get_all_empty(self):
        buf = BytesQueueBuffer()
        assert buf.get_all() == b""

    def test_get_all_single(self):
        buf = BytesQueueBuffer()
        buf.put(b"hello")
        assert buf.get_all() == b"hello"
        assert len(buf) == 0

    def test_get_all_multiple(self):
        buf = BytesQueueBuffer()
        buf.put(b"a")
        buf.put(b"b")
        buf.put(b"c")
        assert buf.get_all() == b"abc"
        assert len(buf) == 0

    def test_exact_chunk_size(self):
        buf = BytesQueueBuffer()
        buf.put(b"abc")
        assert buf.get(3) == b"abc"


class TestIsFpClosed:
    def test_closed_true(self):
        fp = BytesIO(b"data")
        fp.close()
        assert is_fp_closed(fp) is True

    def test_closed_false(self):
        fp = BytesIO(b"data")
        assert is_fp_closed(fp) is False

    def test_no_closed_attr_fp_none(self):
        class FakeFP:
            fp = None
        assert is_fp_closed(FakeFP()) is True

    def test_no_closed_attr_fp_present(self):
        class FakeFP:
            fp = object()
        assert is_fp_closed(FakeFP()) is False


class TestDecoders:
    def test_gzip_decode(self):
        data = b"Hello, World!"
        compressed = gzip.compress(data)
        decoder = GzipDecoder()
        result = decoder.decompress(compressed)
        assert result == data

    def test_deflate_decode(self):
        data = b"Hello, World!"
        compressed = zlib.compress(data)
        decoder = DeflateDecoder()
        result = decoder.decompress(compressed)
        assert result == data

    def test_deflate_raw_fallback(self):
        data = b"Hello, World!"
        compressed = deflate2_compress(data)
        decoder = DeflateDecoder()
        result = decoder.decompress(compressed)
        assert result == data

    def test_get_decoder_gzip(self):
        decoder = _get_decoder("gzip")
        assert isinstance(decoder, GzipDecoder)

    def test_get_decoder_x_gzip(self):
        decoder = _get_decoder("x-gzip")
        assert isinstance(decoder, GzipDecoder)

    def test_get_decoder_deflate(self):
        decoder = _get_decoder("deflate")
        assert isinstance(decoder, DeflateDecoder)

    @pytest.mark.skipif(brotli is None, reason="brotli not installed")
    def test_get_decoder_br(self):
        decoder = _get_decoder("br")
        assert type(decoder).__name__ == "BrotliDecoder"

    @pytest.mark.skipif(not HAS_ZSTD, reason="zstd not installed")
    def test_get_decoder_zstd(self):
        decoder = _get_decoder("zstd")
        assert type(decoder).__name__ == "ZstdDecoder"

    def test_content_decoders_list(self):
        assert "gzip" in CONTENT_DECODERS
        assert "deflate" in CONTENT_DECODERS
        assert "x-gzip" in CONTENT_DECODERS


class TestWaterHTTPResponse:
    def test_cache_content(self):
        r = WaterHTTPResponse(b"foo")
        assert r._body == b"foo"
        assert r.data == b"foo"

    def test_preload_from_fp(self):
        fp = BytesIO(b"bar")
        r = WaterHTTPResponse(fp, preload_content=True)
        assert r.data == b"bar"
        assert r._body == b"bar"

    def test_no_preload(self):
        fp = BytesIO(b"baz")
        r = WaterHTTPResponse(fp, preload_content=False)
        assert r._body is None
        assert r.data == b"baz"

    def test_default_empty(self):
        r = WaterHTTPResponse()
        assert r.data is None

    def test_none_body(self):
        r = WaterHTTPResponse(None)
        assert r.data is None

    def test_status(self):
        r = WaterHTTPResponse(b"", status=200)
        assert r.status == 200

    def test_reason(self):
        r = WaterHTTPResponse(b"", status=200, reason="OK")
        assert r.reason == "OK"

    def test_headers(self):
        r = WaterHTTPResponse(b"", headers={"Content-Type": "text/html"})
        assert r.headers["content-type"] == "text/html"

    def test_json(self):
        r = WaterHTTPResponse(b'{"key": "value"}')
        assert r.json() == {"key": "value"}

    def test_json_list(self):
        r = WaterHTTPResponse(b'[1, 2, 3]')
        assert r.json() == [1, 2, 3]

    def test_read_reference(self):
        fp = BytesIO(b"foo")
        r = WaterHTTPResponse(fp, preload_content=False)
        assert r.read(0) == b""
        assert r.read(1) == b"f"
        assert r.read(2) == b"oo"
        assert r.read() == b""

    @pytest.mark.parametrize("read_args", ((), (None,), (-1,)))
    def test_read_until_eof(self, read_args):
        fp = BytesIO(b"foo")
        r = WaterHTTPResponse(fp, preload_content=False)
        assert r.read(*read_args) == b"foo"

    def test_read1(self):
        fp = BytesIO(b"foobar")
        r = WaterHTTPResponse(fp, preload_content=False)
        assert r.read1(0) == b""
        assert r.read1(1) == b"f"
        assert r.read1(2) == b"oo"
        assert r.read1() == b"bar"

    def test_stream(self):
        fp = BytesIO(b"hello world")
        r = WaterHTTPResponse(fp, preload_content=False)
        chunks = list(r.stream(amt=5))
        combined = b"".join(chunks)
        assert combined == b"hello world"

    def test_stream_empty(self):
        fp = BytesIO(b"")
        r = WaterHTTPResponse(fp, preload_content=False)
        chunks = list(r.stream())
        assert chunks == []

    def test_gzip_decode(self):
        body = b"compressed body content"
        compressed = gzip.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "gzip"},
            preload_content=False,
        )
        assert r.read() == body

    def test_gzip_preloaded(self):
        body = b"preloaded gzip"
        compressed = gzip.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "gzip"},
            preload_content=True,
        )
        assert r.data == body

    def test_deflate_decode(self):
        body = b"deflate body content"
        compressed = zlib.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "deflate"},
            preload_content=False,
        )
        assert r.read() == body

    def test_raw_deflate_decode(self):
        body = b"raw deflate body"
        compressed = deflate2_compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "deflate"},
            preload_content=False,
        )
        assert r.read() == body

    def test_decode_bad_data(self):
        fp = BytesIO(b"\x00" * 10)
        with pytest.raises(DecodeError):
            WaterHTTPResponse(fp, headers={"content-encoding": "deflate"})

    def test_no_decode_content(self):
        body = b"not decoded"
        compressed = gzip.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "gzip"},
            preload_content=False,
            decode_content=False,
        )
        result = r.read()
        assert result == compressed

    @pytest.mark.skipif(brotli is None, reason="brotli not installed")
    def test_brotli_decode(self):
        body = b"brotli compressed data here"
        compressed = brotli.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "br"},
            preload_content=False,
        )
        assert r.read() == body

    @pytest.mark.skipif(not HAS_ZSTD, reason="zstd not installed")
    def test_zstd_decode(self):
        body = b"zstd compressed data here"
        compressed = zstd_compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "zstd"},
            preload_content=False,
        )
        assert r.read() == body

    def test_content_length_enforcement(self):
        fp = BytesIO(b"short")
        r = WaterHTTPResponse(
            fp,
            headers={"content-length": "100"},
            preload_content=False,
            enforce_content_length=True,
        )
        from waterhttp.exceptions import ProtocolError
        with pytest.raises((IncompleteRead, ProtocolError)):
            r.read(10)

    def test_content_length_head_request(self):
        r = WaterHTTPResponse(
            b"",
            headers={"content-length": "100"},
            request_method="HEAD",
        )
        assert r.length_remaining == 0

    def test_content_length_204(self):
        r = WaterHTTPResponse(b"", status=204, headers={"content-length": "0"})
        assert r.length_remaining == 0

    def test_content_length_304(self):
        r = WaterHTTPResponse(b"", status=304, headers={"content-length": "0"})
        assert r.length_remaining == 0

    def test_content_length_1xx(self):
        r = WaterHTTPResponse(b"", status=100, headers={"content-length": "0"})
        assert r.length_remaining == 0

    def test_content_length_multiple_matching(self):
        r = WaterHTTPResponse(
            b"ok",
            headers={"content-length": "2, 2"},
            preload_content=False,
        )
        assert r.length_remaining == 2

    def test_content_length_multiple_nonmatching(self):
        with pytest.raises(InvalidHeader):
            WaterHTTPResponse(
                b"",
                headers={"content-length": "2, 3"},
                preload_content=False,
            )

    def test_redirect_statuses(self):
        for status in [301, 302, 303, 307, 308]:
            r = WaterHTTPResponse(
                b"", status=status, headers={"location": "/new"}
            )
            assert r.get_redirect_location() == "/new"

    def test_not_redirect(self):
        r = WaterHTTPResponse(b"", status=200)
        assert r.get_redirect_location() is False

    def test_redirect_no_location(self):
        r = WaterHTTPResponse(b"", status=301)
        assert r.get_redirect_location() is None

    def test_url_property(self):
        r = WaterHTTPResponse(b"", request_url="http://example.com")
        assert r.url == "http://example.com"

    def test_url_setter(self):
        r = WaterHTTPResponse(b"")
        r.url = "http://new.com"
        assert r.url == "http://new.com"

    def test_tell(self):
        fp = BytesIO(b"hello")
        r = WaterHTTPResponse(fp, preload_content=False)
        assert r.tell() == 0
        r.read(3)
        assert r.tell() == 3

    def test_closed_no_fp(self):
        r = WaterHTTPResponse(b"body")
        assert r.closed is True

    def test_closed_with_fp(self):
        fp = BytesIO(b"body")
        r = WaterHTTPResponse(fp, preload_content=False)
        assert r.closed is False
        r.close()
        assert r.closed is True

    def test_close_connection(self):
        class MockConn:
            closed = False
            def close(self):
                self.closed = True

        conn = MockConn()
        fp = BytesIO(b"data")
        r = WaterHTTPResponse(fp, preload_content=False, connection=conn)
        r.close()
        assert conn.closed is True

    def test_readable(self):
        r = WaterHTTPResponse(b"")
        assert r.readable() is True

    def test_getheaders(self):
        r = WaterHTTPResponse(b"", headers={"X-Test": "val"})
        h = r.getheaders()
        assert h["x-test"] == "val"

    def test_getheader(self):
        r = WaterHTTPResponse(b"", headers={"X-Test": "val"})
        assert r.getheader("X-Test") == "val"
        assert r.getheader("missing", "default") == "default"

    def test_info(self):
        r = WaterHTTPResponse(b"", headers={"X-Test": "val"})
        assert r.info()["x-test"] == "val"

    def test_geturl(self):
        r = WaterHTTPResponse(b"", request_url="http://example.com")
        assert r.geturl() == "http://example.com"

    def test_release_conn(self):
        class MockPool:
            returned = None
            def _return_conn(self, conn):
                self.returned = conn

        pool = MockPool()
        conn = object()
        fp = BytesIO(b"data")
        r = WaterHTTPResponse(fp, preload_content=False, pool=pool, connection=conn)
        r.release_conn()
        assert pool.returned is conn
        assert r._connection is None

    def test_release_conn_no_pool(self):
        r = WaterHTTPResponse(b"data")
        r.release_conn()

    def test_drain_conn(self):
        fp = BytesIO(b"data to drain")
        r = WaterHTTPResponse(fp, preload_content=False)
        r.drain_conn()

    def test_chunked_header_detection(self):
        r = WaterHTTPResponse(
            b"",
            headers={"transfer-encoding": "chunked"},
            preload_content=False,
        )
        assert r.chunked is True

    def test_not_chunked(self):
        r = WaterHTTPResponse(b"", headers={})
        assert r.chunked is False

    def test_read_chunked_not_chunked_raises(self):
        fp = BytesIO(b"data")
        r = WaterHTTPResponse(fp, preload_content=False)
        with pytest.raises(ResponseNotChunked):
            list(r.read_chunked())

    def test_readinto(self):
        fp = BytesIO(b"hello")
        r = WaterHTTPResponse(fp, preload_content=False)
        buf = bytearray(3)
        n = r.readinto(buf)
        assert n == 3
        assert buf == b"hel"

    def test_readinto_empty(self):
        fp = BytesIO(b"")
        r = WaterHTTPResponse(fp, preload_content=False)
        buf = bytearray(3)
        n = r.readinto(buf)
        assert n == 0

    def test_iter(self):
        fp = BytesIO(b"line1\nline2\nline3")
        r = WaterHTTPResponse(fp, preload_content=False)
        lines = list(r)
        assert lines == [b"line1\n", b"line2\n", b"line3"]

    def test_fileno_raises_no_fp(self):
        r = WaterHTTPResponse(b"body")
        with pytest.raises(OSError):
            r.fileno()

    def test_gzip_streaming(self):
        body = b"streamed gzip content" * 100
        compressed = gzip.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "gzip"},
            preload_content=False,
        )
        chunks = list(r.stream(amt=64))
        assert b"".join(chunks) == body

    def test_from_httplib_basic(self):
        import http.client
        import socket as _socket

        class FakeSocket:
            def __init__(self, data: bytes):
                self._fp = BytesIO(data)
            def makefile(self, mode: str) -> BytesIO:
                return self._fp
            def close(self) -> None:
                pass

        raw_data = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello"
        sock = FakeSocket(raw_data)
        resp = http.client.HTTPResponse(sock)
        resp.begin()
        r = WaterHTTPResponse.from_httplib(resp)
        assert r.status == 200
        assert r.data == b"hello"

    def test_retries_attribute(self):
        r = WaterHTTPResponse(b"", retries=Retry(3))
        assert r.retries is not None
        assert r.retries.total == 3

    def test_version(self):
        r = WaterHTTPResponse(b"", version=11)
        assert r.version == 11

    def test_content_length_negative(self):
        r = WaterHTTPResponse(
            b"",
            headers={"content-length": "-1"},
            preload_content=False,
        )
        assert r.length_remaining is None

    def test_content_length_invalid(self):
        r = WaterHTTPResponse(
            b"",
            headers={"content-length": "abc"},
            preload_content=False,
        )
        assert r.length_remaining is None

    def test_x_gzip_decode(self):
        body = b"x-gzip content"
        compressed = gzip.compress(body)
        fp = BytesIO(compressed)
        r = WaterHTTPResponse(
            fp,
            headers={"content-encoding": "x-gzip"},
            preload_content=False,
        )
        assert r.read() == body
