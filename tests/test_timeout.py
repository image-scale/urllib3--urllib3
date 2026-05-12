from __future__ import annotations

import time

import pytest

from waterhttp.timeout import Timeout, DEFAULT_TIMEOUT
from waterhttp.exceptions import TimeoutStateError


class TestTimeout:
    def test_total_timeout(self):
        t = Timeout(total=5)
        assert t.total == 5
        assert t._connect is DEFAULT_TIMEOUT
        assert t._read is DEFAULT_TIMEOUT

    def test_connect_and_read(self):
        t = Timeout(connect=3, read=10)
        assert t._connect == 3
        assert t._read == 10
        assert t.total is None

    def test_from_float(self):
        t = Timeout.from_float(5)
        assert t._connect == 5
        assert t._read == 5

    def test_from_float_none(self):
        t = Timeout.from_float(None)
        assert t._connect is None
        assert t._read is None

    def test_clone_returns_independent_copy(self):
        t = Timeout(connect=3, read=10, total=15)
        cloned = t.clone()
        assert cloned._connect == 3
        assert cloned._read == 10
        assert cloned.total == 15
        assert cloned is not t
        assert cloned._start_connect is None

    def test_start_connect(self):
        t = Timeout(total=5)
        start = t.start_connect()
        assert isinstance(start, float)
        assert start > 0

    def test_start_connect_twice_raises(self):
        t = Timeout(total=5)
        t.start_connect()
        with pytest.raises(TimeoutStateError, match="already been started"):
            t.start_connect()

    def test_get_connect_duration(self):
        t = Timeout(total=5)
        t.start_connect()
        time.sleep(0.01)
        duration = t.get_connect_duration()
        assert duration >= 0.01
        assert duration < 1.0

    def test_get_connect_duration_not_started_raises(self):
        t = Timeout(total=5)
        with pytest.raises(TimeoutStateError, match="has not started"):
            t.get_connect_duration()

    def test_connect_timeout_no_total(self):
        t = Timeout(connect=3)
        assert t.connect_timeout == 3

    def test_connect_timeout_with_total_smaller(self):
        t = Timeout(connect=10, total=5)
        assert t.connect_timeout == 5

    def test_connect_timeout_with_total_larger(self):
        t = Timeout(connect=3, total=10)
        assert t.connect_timeout == 3

    def test_connect_timeout_total_only(self):
        t = Timeout(total=5)
        assert t.connect_timeout == 5

    def test_connect_timeout_none_connect_with_total(self):
        t = Timeout(connect=None, total=5)
        assert t.connect_timeout == 5

    def test_connect_timeout_total_none(self):
        t = Timeout(total=None, connect=3)
        assert t.connect_timeout == 3

    def test_read_timeout_no_total(self):
        t = Timeout(read=10)
        assert t.read_timeout == 10

    def test_read_timeout_none_no_total(self):
        t = Timeout(read=None)
        assert t.read_timeout is None

    def test_read_timeout_with_total_adjusts_for_connect(self):
        t = Timeout(total=10, read=8)
        t.start_connect()
        time.sleep(0.05)
        read_t = t.read_timeout
        assert read_t is not None
        assert read_t <= 8
        assert read_t > 0

    def test_read_timeout_total_only_adjusts(self):
        t = Timeout(total=10)
        t.start_connect()
        time.sleep(0.01)
        read_t = t.read_timeout
        assert read_t is not None
        assert read_t < 10

    def test_read_timeout_total_and_read_not_started(self):
        t = Timeout(total=10, read=5)
        assert t.read_timeout == 5

    def test_read_timeout_total_exceeded_returns_zero(self):
        t = Timeout(total=0.001, read=5)
        t.start_connect()
        time.sleep(0.01)
        assert t.read_timeout == 0

    def test_read_timeout_total_only_not_started_raises(self):
        t = Timeout(total=5)
        with pytest.raises(TimeoutStateError):
            _ = t.read_timeout

    def test_validate_negative_raises(self):
        with pytest.raises(ValueError, match="less than or equal to 0"):
            Timeout(connect=-1)

    def test_validate_zero_raises(self):
        with pytest.raises(ValueError, match="less than or equal to 0"):
            Timeout(read=0)

    def test_validate_boolean_raises(self):
        with pytest.raises(ValueError, match="boolean"):
            Timeout(connect=True)

    def test_validate_false_raises(self):
        with pytest.raises(ValueError, match="boolean"):
            Timeout(connect=False)

    def test_validate_string_raises(self):
        with pytest.raises(ValueError, match="int, float or None"):
            Timeout(connect="foo")  # type: ignore[arg-type]

    def test_none_is_valid(self):
        t = Timeout(connect=None, read=None, total=None)
        assert t._connect is None
        assert t._read is None
        assert t.total is None

    def test_resolve_default_timeout_sentinel(self):
        import socket

        old_default = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(42.0)
            result = Timeout.resolve_default_timeout(DEFAULT_TIMEOUT)
            assert result == 42.0
        finally:
            socket.setdefaulttimeout(old_default)

    def test_resolve_default_timeout_non_sentinel(self):
        result = Timeout.resolve_default_timeout(5.0)
        assert result == 5.0

    def test_resolve_default_timeout_none(self):
        result = Timeout.resolve_default_timeout(None)
        assert result is None

    def test_repr(self):
        t = Timeout(connect=3, read=10, total=15)
        r = repr(t)
        assert "connect=3" in r
        assert "read=10" in r
        assert "total=15" in r

    def test_str_equals_repr(self):
        t = Timeout(connect=3)
        assert str(t) == repr(t)
