from __future__ import annotations

import pytest

from waterhttp.retry import Retry, RequestHistory
from waterhttp.exceptions import (
    ConnectTimeoutError,
    MaxRetryError,
    ReadTimeoutError,
    ResponseError,
    InvalidHeader,
)


class _FakeResponse:
    def __init__(self, status: int = 200, headers: dict | None = None, redirect: str | None = None):
        self.status = status
        self.headers = headers or {}
        self._redirect = redirect

    def get_redirect_location(self) -> str | bool:
        if self._redirect:
            return self._redirect
        return False


class TestRetry:
    def test_default_total(self):
        r = Retry()
        assert r.total == 10

    def test_custom_total(self):
        r = Retry(total=3)
        assert r.total == 3

    def test_increment_decrements_total(self):
        r = Retry(total=3)
        r2 = r.increment(method="GET")
        assert r2.total == 2

    def test_increment_exhausted_raises(self):
        r = Retry(total=0)
        with pytest.raises(MaxRetryError):
            r.increment(method="GET")

    def test_connect_retry_decrements(self):
        r = Retry(total=10, connect=2)
        error = ConnectTimeoutError("connection failed")
        r2 = r.increment(error=error)
        assert r2.connect == 1
        assert r2.total == 9

    def test_read_retry_decrements(self):
        r = Retry(total=10, read=2)
        error = ReadTimeoutError("read timed out")
        r2 = r.increment(method="GET", error=error)
        assert r2.read == 1

    def test_redirect_retry_decrements(self):
        r = Retry(total=10, redirect=3)
        resp = _FakeResponse(status=301, redirect="/new-location")
        r2 = r.increment(method="GET", response=resp)
        assert r2.redirect == 2

    def test_status_retry_decrements(self):
        r = Retry(total=10, status=2, status_forcelist=[500])
        resp = _FakeResponse(status=500)
        r2 = r.increment(method="GET", response=resp)
        assert r2.status == 1

    def test_backoff_time_first_retry(self):
        r = Retry(total=3, backoff_factor=0.1)
        assert r.get_backoff_time() == 0

    def test_backoff_time_after_errors(self):
        r = Retry(
            total=3,
            backoff_factor=0.1,
            history=(
                RequestHistory("GET", "/", ConnectTimeoutError(), None, None),
                RequestHistory("GET", "/", ConnectTimeoutError(), None, None),
            ),
        )
        backoff = r.get_backoff_time()
        assert backoff == pytest.approx(0.2, abs=0.01)

    def test_backoff_max_caps(self):
        r = Retry(
            total=3,
            backoff_factor=100,
            backoff_max=5,
            history=(
                RequestHistory("GET", "/", ConnectTimeoutError(), None, None),
                RequestHistory("GET", "/", ConnectTimeoutError(), None, None),
                RequestHistory("GET", "/", ConnectTimeoutError(), None, None),
            ),
        )
        assert r.get_backoff_time() == 5

    def test_from_int_number(self):
        r = Retry.from_int(3)
        assert r.total == 3

    def test_from_int_retry_passthrough(self):
        original = Retry(total=5)
        r = Retry.from_int(original)
        assert r is original

    def test_from_int_none_returns_default(self):
        r = Retry.from_int(None)
        assert r.total == Retry.DEFAULT.total

    def test_is_retry_status_forcelist(self):
        r = Retry(total=3, status_forcelist=[500, 502])
        assert r.is_retry("GET", 500) is True
        assert r.is_retry("GET", 200) is False

    def test_is_retry_method_not_allowed(self):
        r = Retry(total=3, status_forcelist=[500], allowed_methods=["GET"])
        assert r.is_retry("POST", 500) is False
        assert r.is_retry("GET", 500) is True

    def test_history_tracks_attempts(self):
        r = Retry(total=5)
        error = ConnectTimeoutError("fail")
        r2 = r.increment(method="GET", url="/test", error=error)
        assert len(r2.history) == 1
        assert r2.history[0].method == "GET"
        assert r2.history[0].url == "/test"
        assert r2.history[0].error is error

    def test_new_creates_copy(self):
        r = Retry(total=5, connect=2, read=3)
        r2 = r.new(total=10)
        assert r2.total == 10
        assert r2.connect == 2
        assert r2.read == 3
        assert r2 is not r

    def test_default_class_attribute(self):
        assert isinstance(Retry.DEFAULT, Retry)
        assert Retry.DEFAULT.total == 3

    def test_raise_on_redirect_default(self):
        r = Retry(total=3, redirect=1, raise_on_redirect=True)
        resp = _FakeResponse(status=301, redirect="/new")
        r2 = r.increment(method="GET", response=resp)
        with pytest.raises(MaxRetryError):
            r2.increment(method="GET", response=resp)

    def test_parse_retry_after_integer(self):
        r = Retry()
        assert r.parse_retry_after("120") == 120.0

    def test_parse_retry_after_invalid(self):
        r = Retry()
        with pytest.raises(InvalidHeader):
            r.parse_retry_after("not-a-date-or-number")

    def test_is_exhausted_true(self):
        r = Retry(total=-1)
        assert r.is_exhausted() is True

    def test_is_exhausted_false(self):
        r = Retry(total=3)
        assert r.is_exhausted() is False

    def test_is_exhausted_all_none(self):
        r = Retry(total=None, connect=None, read=None)
        assert r.is_exhausted() is False

    def test_repr(self):
        r = Retry(total=3, connect=1, read=2)
        s = repr(r)
        assert "total=3" in s
        assert "connect=1" in s
        assert "read=2" in s

    def test_total_false_disables_retries(self):
        r = Retry(total=False)
        assert r.redirect == 0
        assert r.raise_on_redirect is False

    def test_redirect_false_sets_zero(self):
        r = Retry(redirect=False)
        assert r.redirect == 0
        assert r.raise_on_redirect is False

    def test_other_error_decrements_other(self):
        r = Retry(total=10, other=2)
        error = Exception("some other error")
        r2 = r.increment(error=error)
        assert r2.other == 1

    def test_increment_records_redirect_location(self):
        r = Retry(total=5, redirect=5)
        resp = _FakeResponse(status=302, redirect="http://other.com/new")
        r2 = r.increment(method="GET", url="/old", response=resp)
        assert r2.history[-1].redirect_location == "http://other.com/new"
        assert r2.history[-1].status == 302

    def test_allowed_methods_none_retries_all(self):
        r = Retry(total=3, status_forcelist=[500], allowed_methods=None)
        assert r.is_retry("POST", 500) is True
        assert r.is_retry("PATCH", 500) is True

    def test_default_allowed_methods(self):
        assert "GET" in Retry.DEFAULT_ALLOWED_METHODS
        assert "HEAD" in Retry.DEFAULT_ALLOWED_METHODS
        assert "POST" not in Retry.DEFAULT_ALLOWED_METHODS

    def test_remove_headers_on_redirect_lowercased(self):
        r = Retry(remove_headers_on_redirect=["Authorization", "Cookie"])
        assert "authorization" in r.remove_headers_on_redirect
        assert "cookie" in r.remove_headers_on_redirect

    def test_parse_retry_after_max_capped(self):
        r = Retry(retry_after_max=60)
        assert r.parse_retry_after("1000") == 60

    def test_backoff_ignores_redirects_in_history(self):
        r = Retry(
            total=3,
            backoff_factor=1,
            history=(
                RequestHistory("GET", "/", None, 301, "/new"),
                RequestHistory("GET", "/new", ConnectTimeoutError(), None, None),
            ),
        )
        assert r.get_backoff_time() == 0

    def test_multiple_increments_to_exhaustion(self):
        r = Retry(total=2)
        r = r.increment(method="GET")
        r = r.increment(method="GET")
        with pytest.raises(MaxRetryError):
            r.increment(method="GET")
