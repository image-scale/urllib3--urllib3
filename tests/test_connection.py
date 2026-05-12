from __future__ import annotations

import socket
import ssl

import pytest

from waterhttp.connection import (
    HTTPConnection,
    HTTPSConnection,
    SCHEME_TO_PORT,
    is_connection_dropped,
    _create_connection,
)
from waterhttp.ssl_helpers import (
    create_ssl_context,
    assert_fingerprint,
    resolve_cert_reqs,
)
from waterhttp.exceptions import SSLError, ConnectTimeoutError, NewConnectionError


class TestSchemeToPort:
    def test_http(self):
        assert SCHEME_TO_PORT["http"] == 80

    def test_https(self):
        assert SCHEME_TO_PORT["https"] == 443


class TestHTTPConnection:
    def test_default_port(self):
        conn = HTTPConnection("example.com")
        assert conn.default_port == 80

    def test_custom_port(self):
        conn = HTTPConnection("example.com", port=8080)
        assert conn.port == 8080

    def test_host(self):
        conn = HTTPConnection("example.com")
        assert conn.host == "example.com"

    def test_is_closed_initially(self):
        conn = HTTPConnection("example.com")
        assert conn.is_closed is True

    def test_is_connected_initially_false(self):
        conn = HTTPConnection("example.com")
        assert conn.is_connected is False

    def test_is_connection_dropped_no_sock(self):
        conn = HTTPConnection("example.com")
        assert is_connection_dropped(conn) is True

    def test_default_socket_options(self):
        conn = HTTPConnection("example.com")
        assert conn.socket_options is not None
        assert (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) in conn.socket_options

    def test_custom_socket_options(self):
        opts = [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)]
        conn = HTTPConnection("example.com", socket_options=opts)
        assert conn.socket_options == opts

    def test_set_tunnel(self):
        conn = HTTPConnection("proxy.com", port=3128)
        conn.set_tunnel("target.com", port=443, scheme="https")
        assert conn._tunnel_host == "target.com"
        assert conn._tunnel_port == 443
        assert conn._tunnel_scheme == "https"

    def test_has_connected_to_proxy_false(self):
        conn = HTTPConnection("example.com")
        assert conn.has_connected_to_proxy is False

    def test_timeout_float(self):
        conn = HTTPConnection("example.com", timeout=5.0)
        assert conn.timeout == 5.0

    def test_timeout_none(self):
        conn = HTTPConnection("example.com", timeout=None)
        assert conn.timeout is None

    def test_blocksize(self):
        conn = HTTPConnection("example.com", blocksize=4096)
        assert conn.blocksize == 4096

    def test_connect_nonexistent_host(self):
        conn = HTTPConnection("nonexistent.invalid.host.test", port=1)
        with pytest.raises((NewConnectionError, OSError)):
            conn.connect()


class TestHTTPSConnection:
    def test_default_port(self):
        conn = HTTPSConnection("example.com")
        assert conn.default_port == 443

    def test_ssl_attributes(self):
        conn = HTTPSConnection(
            "example.com",
            cert_file="/path/to/cert",
            key_file="/path/to/key",
            ca_certs="/path/to/ca",
        )
        assert conn.cert_file == "/path/to/cert"
        assert conn.key_file == "/path/to/key"
        assert conn.ca_certs == "/path/to/ca"

    def test_fingerprint_attribute(self):
        conn = HTTPSConnection(
            "example.com",
            assert_fingerprint="AA:BB:CC",
        )
        assert conn.assert_fingerprint_value == "AA:BB:CC"

    def test_ssl_context_passthrough(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        conn = HTTPSConnection("example.com", ssl_context=ctx)
        assert conn.ssl_context is ctx

    def test_is_closed_initially(self):
        conn = HTTPSConnection("example.com")
        assert conn.is_closed is True


class TestCreateSSLContext:
    def test_returns_ssl_context(self):
        ctx = create_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

    def test_default_verify_mode(self):
        ctx = create_ssl_context()
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_cert_none_mode(self):
        ctx = create_ssl_context(cert_reqs=ssl.CERT_NONE)
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_minimum_tls_version(self):
        ctx = create_ssl_context()
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_custom_minimum_version(self):
        ctx = create_ssl_context(ssl_minimum_version=ssl.TLSVersion.TLSv1_3)
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_3

    def test_no_compression(self):
        ctx = create_ssl_context()
        assert ctx.options & ssl.OP_NO_COMPRESSION


class TestAssertFingerprint:
    def test_valid_sha256(self):
        import hashlib
        cert = b"test certificate data"
        fp = hashlib.sha256(cert).hexdigest()
        assert_fingerprint(cert, fp)

    def test_valid_sha1(self):
        import hashlib
        cert = b"test certificate data"
        fp = hashlib.sha1(cert).hexdigest()
        assert_fingerprint(cert, fp)

    def test_invalid_fingerprint_raises(self):
        cert = b"test certificate data"
        bad_fp = "a" * 64
        with pytest.raises(SSLError, match="Fingerprints did not match"):
            assert_fingerprint(cert, bad_fp)

    def test_no_cert_raises(self):
        with pytest.raises(SSLError, match="No certificate"):
            assert_fingerprint(None, "a" * 64)

    def test_invalid_length_raises(self):
        with pytest.raises(SSLError, match="invalid length"):
            assert_fingerprint(b"cert", "abc")

    def test_colon_separated_fingerprint(self):
        import hashlib
        cert = b"test certificate data"
        fp = hashlib.sha256(cert).hexdigest()
        colon_fp = ":".join(fp[i:i+2] for i in range(0, len(fp), 2))
        assert_fingerprint(cert, colon_fp)


class TestResolveCertReqs:
    def test_none_returns_required(self):
        assert resolve_cert_reqs(None) == ssl.CERT_REQUIRED

    def test_string_required(self):
        assert resolve_cert_reqs("REQUIRED") == ssl.CERT_REQUIRED

    def test_string_none_val(self):
        assert resolve_cert_reqs("NONE") == ssl.CERT_NONE

    def test_string_optional(self):
        assert resolve_cert_reqs("OPTIONAL") == ssl.CERT_OPTIONAL

    def test_int_passthrough(self):
        assert resolve_cert_reqs(ssl.CERT_NONE) == ssl.CERT_NONE
