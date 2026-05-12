from __future__ import annotations

import pytest

from waterhttp.url import Url, parse_url, _encode_target, _remove_dot_segments
from waterhttp.exceptions import LocationParseError


class TestUrl:
    def test_url_with_all_components(self):
        u = Url("https", "user:pass", "host.com", 80, "/path", "query", "fragment")
        assert u.scheme == "https"
        assert u.auth == "user:pass"
        assert u.host == "host.com"
        assert u.port == 80
        assert u.path == "/path"
        assert u.query == "query"
        assert u.fragment == "fragment"

    def test_url_defaults_all_none(self):
        u = Url()
        assert u.scheme is None
        assert u.auth is None
        assert u.host is None
        assert u.port is None
        assert u.path is None
        assert u.query is None
        assert u.fragment is None

    def test_scheme_is_lowercased(self):
        u = Url("HTTP")
        assert u.scheme == "http"

    def test_path_gets_leading_slash(self):
        u = Url(path="foo/bar")
        assert u.path == "/foo/bar"

    def test_path_already_has_slash(self):
        u = Url(path="/foo/bar")
        assert u.path == "/foo/bar"

    def test_request_uri_with_path_and_query(self):
        u = Url(path="/path", query="q=1")
        assert u.request_uri == "/path?q=1"

    def test_request_uri_defaults_to_slash(self):
        u = Url()
        assert u.request_uri == "/"

    def test_request_uri_path_only(self):
        u = Url(path="/hello")
        assert u.request_uri == "/hello"

    def test_netloc_host_only(self):
        u = Url(host="example.com")
        assert u.netloc == "example.com"

    def test_netloc_host_and_port(self):
        u = Url(host="example.com", port=8080)
        assert u.netloc == "example.com:8080"

    def test_netloc_no_host(self):
        u = Url()
        assert u.netloc is None

    def test_authority_with_auth(self):
        u = Url(auth="user:pass", host="host.com", port=80)
        assert u.authority == "user:pass@host.com:80"

    def test_authority_no_auth(self):
        u = Url(host="host.com")
        assert u.authority == "host.com"

    def test_authority_no_host(self):
        u = Url()
        assert u.authority is None

    def test_hostname_alias(self):
        u = Url(host="example.com")
        assert u.hostname == "example.com"

    def test_url_reconstruction(self):
        u = Url("https", "user:pass", "host.com", 80, "/path", "query", "frag")
        assert u.url == "https://user:pass@host.com:80/path?query#frag"

    def test_url_reconstruction_minimal(self):
        u = Url(host="example.com", path="/")
        assert u.url == "example.com/"

    def test_url_reconstruction_scheme_only(self):
        u = Url(scheme="http", host="example.com")
        assert u.url == "http://example.com"

    def test_str_returns_url(self):
        u = Url("http", host="example.com", path="/")
        assert str(u) == "http://example.com/"

    def test_url_is_namedtuple(self):
        u = Url("http", host="example.com", port=80)
        assert u[0] == "http"
        assert u[2] == "example.com"
        assert u[3] == 80


class TestParseUrl:
    @pytest.mark.parametrize(
        "url, expected",
        [
            (
                "http://google.com/mail",
                Url("http", host="google.com", path="/mail"),
            ),
            (
                "http://google.com/mail/",
                Url("http", host="google.com", path="/mail/"),
            ),
            (
                "http://google.com",
                Url("http", host="google.com"),
            ),
            (
                "http://google.com/",
                Url("http", host="google.com", path="/"),
            ),
        ],
    )
    def test_basic_urls(self, url, expected):
        result = parse_url(url)
        assert result == expected

    def test_full_url_components(self):
        result = parse_url("http://user:pass@host.com:8080/path?query=1#frag")
        assert result.scheme == "http"
        assert result.auth == "user:pass"
        assert result.host == "host.com"
        assert result.port == 8080
        assert result.path == "/path"
        assert result.query == "query=1"
        assert result.fragment == "frag"

    def test_scheme_lowercased(self):
        result = parse_url("HTTP://host.com/")
        assert result.scheme == "http"

    def test_host_lowercased(self):
        result = parse_url("http://GOOGLE.COM/")
        assert result.host == "google.com"

    def test_no_scheme_with_authority(self):
        result = parse_url("google.com:80")
        assert result.scheme is None
        assert result.host == "google.com"
        assert result.port == 80

    def test_no_scheme_no_port(self):
        result = parse_url("google.com/mail")
        assert result.host == "google.com"
        assert result.path == "/mail"

    def test_path_only(self):
        result = parse_url("/foo?bar")
        assert result.scheme is None
        assert result.host is None
        assert result.path == "/foo"
        assert result.query == "bar"

    def test_empty_string(self):
        result = parse_url("")
        assert result == Url()

    def test_port_as_integer(self):
        result = parse_url("http://host:8080/")
        assert result.port == 8080
        assert isinstance(result.port, int)

    def test_port_zero(self):
        result = parse_url("http://host:0/")
        assert result.port == 0

    def test_port_65535(self):
        result = parse_url("http://host:65535/")
        assert result.port == 65535

    def test_invalid_port_letters(self):
        with pytest.raises(LocationParseError):
            parse_url("http://host:abc/")

    def test_invalid_port_negative(self):
        with pytest.raises(LocationParseError):
            parse_url("http://host:-1/")

    def test_invalid_port_too_large(self):
        with pytest.raises(LocationParseError):
            parse_url("http://host:65536/")

    def test_ipv6_host(self):
        result = parse_url("http://[::1]/")
        assert result.host == "[::1]"
        assert result.path == "/"

    def test_ipv6_host_with_port(self):
        result = parse_url("http://[::1]:8080/")
        assert result.host == "[::1]"
        assert result.port == 8080

    def test_ipv6_full(self):
        result = parse_url("http://[2001:db8::1]:443/path")
        assert result.host == "[2001:db8::1]"
        assert result.port == 443

    def test_scheme_only(self):
        result = parse_url("http://")
        assert result.scheme == "http"
        assert result.host is None

    def test_https_scheme(self):
        result = parse_url("https://secure.example.com/login")
        assert result.scheme == "https"
        assert result.host == "secure.example.com"

    def test_query_without_path(self):
        result = parse_url("http://host?query")
        assert result.host == "host"
        assert result.query == "query"
        assert result.path == ""

    def test_fragment_without_path(self):
        result = parse_url("http://host#frag")
        assert result.host == "host"
        assert result.fragment == "frag"
        assert result.path == ""

    def test_auth_without_password(self):
        result = parse_url("http://user@host.com/")
        assert result.auth == "user"

    def test_multiple_at_signs(self):
        result = parse_url("http://user:p%40ss@host.com/")
        assert result.auth == "user:p%40ss"
        assert result.host == "host.com"

    def test_url_with_port_no_trailing_slash(self):
        result = parse_url("http://host:80")
        assert result.host == "host"
        assert result.port == 80

    def test_leading_zeros_stripped_from_port(self):
        result = parse_url("http://host:0080/")
        assert result.port == 80

    @pytest.mark.parametrize(
        "url, expected_path",
        [
            ("http://host/a/b/../c", "/a/c"),
            ("http://host/a/./b", "/a/b"),
            ("http://host/a/b/./c/../d", "/a/b/d"),
        ],
    )
    def test_dot_segment_removal(self, url, expected_path):
        result = parse_url(url)
        assert result.path == expected_path

    def test_roundtrip(self):
        original = "http://user:pass@host.com:8080/path?query=1#frag"
        result = parse_url(original)
        assert result.url == original

    def test_url_without_scheme_roundtrip(self):
        result = parse_url("host.com:80/path")
        assert result.host == "host.com"
        assert result.port == 80
        assert result.path == "/path"


class TestRemoveDotSegments:
    def test_single_dot(self):
        assert _remove_dot_segments("/a/./b") == "/a/b"

    def test_double_dot(self):
        assert _remove_dot_segments("/a/b/../c") == "/a/c"

    def test_leading_double_dot(self):
        assert _remove_dot_segments("/a/../b") == "/b"

    def test_trailing_dot(self):
        assert _remove_dot_segments("/a/b/.") == "/a/b/"

    def test_trailing_double_dot(self):
        assert _remove_dot_segments("/a/b/..") == "/a/"


class TestEncodeTarget:
    def test_simple_path(self):
        assert _encode_target("/foo/bar") == "/foo/bar"

    def test_path_with_query(self):
        assert _encode_target("/foo?bar=baz") == "/foo?bar=baz"

    def test_invalid_target_raises(self):
        with pytest.raises(LocationParseError):
            _encode_target("no-leading-slash")
