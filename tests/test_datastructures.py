from __future__ import annotations

import pytest

from waterhttp.datastructures import HTTPHeaderDict, RecentlyUsedContainer


class TestRecentlyUsedContainer:
    def test_maxsize_eviction(self):
        d = RecentlyUsedContainer(maxsize=3)
        for i in range(4):
            d[i] = str(i)
        assert len(d) == 3
        assert 0 not in d.keys()
        assert 3 in d.keys()

    def test_getitem_marks_recently_used(self):
        d = RecentlyUsedContainer(maxsize=3)
        d[1] = "a"
        d[2] = "b"
        d[3] = "c"
        _ = d[1]
        d[4] = "d"
        assert 1 in d.keys()
        assert 2 not in d.keys()

    def test_dispose_func_called_on_eviction(self):
        disposed = []
        d = RecentlyUsedContainer(maxsize=2, dispose_func=disposed.append)
        d["a"] = "1"
        d["b"] = "2"
        d["c"] = "3"
        assert "1" in disposed

    def test_dispose_func_called_on_delete(self):
        disposed = []
        d = RecentlyUsedContainer(maxsize=5, dispose_func=disposed.append)
        d["a"] = "val"
        del d["a"]
        assert "val" in disposed

    def test_clear_disposes_all(self):
        disposed = []
        d = RecentlyUsedContainer(maxsize=5, dispose_func=disposed.append)
        d["a"] = "1"
        d["b"] = "2"
        d.clear()
        assert len(d) == 0
        assert len(disposed) == 2

    def test_iter_raises_not_implemented(self):
        d = RecentlyUsedContainer(maxsize=5)
        with pytest.raises(NotImplementedError):
            iter(d)

    def test_keys_returns_set(self):
        d = RecentlyUsedContainer(maxsize=5)
        d["a"] = "1"
        d["b"] = "2"
        assert d.keys() == {"a", "b"}

    def test_len(self):
        d = RecentlyUsedContainer(maxsize=5)
        assert len(d) == 0
        d["a"] = "1"
        assert len(d) == 1

    def test_setitem_overwrite(self):
        d = RecentlyUsedContainer(maxsize=5)
        d["a"] = "1"
        d["a"] = "2"
        assert d["a"] == "2"
        assert len(d) == 1

    def test_getitem_keyerror(self):
        d = RecentlyUsedContainer(maxsize=5)
        with pytest.raises(KeyError):
            d["missing"]

    def test_maxsize_zero(self):
        disposed = []
        d = RecentlyUsedContainer(maxsize=0, dispose_func=disposed.append)
        d["a"] = "1"
        assert len(d) == 0
        assert "1" in disposed

    def test_dispose_on_overwrite(self):
        disposed = []
        d = RecentlyUsedContainer(maxsize=5, dispose_func=disposed.append)
        d["a"] = "old"
        d["a"] = "new"
        assert "old" in disposed
        assert d["a"] == "new"


class TestHTTPHeaderDict:
    @pytest.fixture()
    def d(self) -> HTTPHeaderDict:
        header_dict = HTTPHeaderDict(Cookie="foo")
        header_dict.add("cookie", "bar")
        return header_dict

    def test_case_insensitive_get(self, d):
        assert d["Cookie"] == "foo, bar"
        assert d["cookie"] == "foo, bar"
        assert d["COOKIE"] == "foo, bar"

    def test_setitem_overwrites(self):
        d = HTTPHeaderDict()
        d["Content-Type"] = "text/html"
        d["content-type"] = "application/json"
        assert d["Content-Type"] == "application/json"
        assert len(d) == 1

    def test_add_without_overwrite(self):
        d = HTTPHeaderDict()
        d["Accept"] = "text/html"
        d.add("Accept", "application/json")
        assert d["Accept"] == "text/html, application/json"

    def test_add_with_combine(self):
        d = HTTPHeaderDict()
        d["Set-Cookie"] = "a=1"
        d.add("Set-Cookie", "b=2")
        d.add("Set-Cookie", "c=3", combine=True)
        items = list(d.iteritems())
        assert len(items) == 2
        assert items[0] == ("Set-Cookie", "a=1")
        assert items[1] == ("Set-Cookie", "b=2, c=3")

    def test_getlist(self, d):
        values = d.getlist("cookie")
        assert values == ["foo", "bar"]

    def test_getlist_missing_returns_empty(self):
        d = HTTPHeaderDict()
        assert d.getlist("missing") == []

    def test_iteritems_yields_duplicates(self, d):
        items = list(d.iteritems())
        assert len(items) == 2
        assert items[0] == ("Cookie", "foo")
        assert items[1] == ("Cookie", "bar")

    def test_itermerged_joins(self, d):
        merged = list(d.itermerged())
        assert len(merged) == 1
        assert merged[0] == ("Cookie", "foo, bar")

    def test_copy_is_independent(self, d):
        d2 = d.copy()
        d2["New-Header"] = "value"
        assert "New-Header" not in d
        assert d2["Cookie"] == "foo, bar"

    def test_eq_case_insensitive(self):
        d1 = HTTPHeaderDict(Foo="bar")
        d2 = HTTPHeaderDict(foo="bar")
        assert d1 == d2

    def test_eq_with_dict(self):
        d1 = HTTPHeaderDict(Foo="bar")
        assert d1 == {"Foo": "bar"}

    def test_ne(self):
        d1 = HTTPHeaderDict(Foo="bar")
        d2 = HTTPHeaderDict(Foo="baz")
        assert d1 != d2

    def test_extend_from_dict(self):
        d = HTTPHeaderDict()
        d.extend({"Content-Type": "text/html", "Accept": "application/json"})
        assert d["Content-Type"] == "text/html"
        assert d["Accept"] == "application/json"

    def test_extend_from_iterable(self):
        d = HTTPHeaderDict()
        d.extend([("X-Header", "val1"), ("X-Header", "val2")])
        assert d["X-Header"] == "val1, val2"

    def test_extend_from_header_dict(self):
        d1 = HTTPHeaderDict(Foo="bar")
        d1.add("Foo", "baz")
        d2 = HTTPHeaderDict()
        d2.extend(d1)
        assert d2.getlist("Foo") == ["bar", "baz"]

    def test_contains_case_insensitive(self):
        d = HTTPHeaderDict(Foo="bar")
        assert "Foo" in d
        assert "foo" in d
        assert "FOO" in d
        assert "Bar" not in d

    def test_or_merge(self):
        d1 = HTTPHeaderDict(Foo="bar")
        d2 = HTTPHeaderDict(Baz="qux")
        merged = d1 | d2
        assert merged["Foo"] == "bar"
        assert merged["Baz"] == "qux"
        assert "Baz" not in d1

    def test_ior_extend(self):
        d1 = HTTPHeaderDict(Foo="bar")
        d1 |= HTTPHeaderDict(Baz="qux")
        assert d1["Baz"] == "qux"

    def test_len_unique_keys(self):
        d = HTTPHeaderDict()
        d["A"] = "1"
        d.add("A", "2")
        d["B"] = "3"
        assert len(d) == 2

    def test_iter_yields_original_case(self):
        d = HTTPHeaderDict()
        d["Content-Type"] = "text/html"
        d["accept"] = "application/json"
        keys = list(d)
        assert "Content-Type" in keys or "content-type" in keys
        assert len(keys) == 2

    def test_delitem(self):
        d = HTTPHeaderDict(Foo="bar")
        del d["foo"]
        assert "Foo" not in d

    def test_discard_missing_key(self):
        d = HTTPHeaderDict()
        d.discard("missing")

    def test_init_from_header_dict(self):
        d1 = HTTPHeaderDict(Foo="bar")
        d1.add("Foo", "baz")
        d2 = HTTPHeaderDict(d1)
        assert d2.getlist("Foo") == ["bar", "baz"]

    def test_init_with_kwargs(self):
        d = HTTPHeaderDict(Foo="bar", Baz="qux")
        assert d["Foo"] == "bar"
        assert d["Baz"] == "qux"

    def test_repr(self):
        d = HTTPHeaderDict(Foo="bar")
        r = repr(d)
        assert "HTTPHeaderDict" in r
        assert "Foo" in r

    def test_items_view(self):
        d = HTTPHeaderDict(Foo="bar")
        d.add("Foo", "baz")
        items = d.items()
        assert len(items) == 2
        assert ("Foo", "bar") in items
        assert ("Foo", "baz") in items

    def test_setdefault(self):
        d = HTTPHeaderDict()
        result = d.setdefault("Foo", "bar")
        assert result == "bar"
        assert d["Foo"] == "bar"
        result2 = d.setdefault("Foo", "new")
        assert result2 == "bar"

    def test_getheaders_alias(self):
        d = HTTPHeaderDict(Foo="bar")
        assert d.getheaders("Foo") == ["bar"]

    def test_get_all_alias(self):
        d = HTTPHeaderDict(Foo="bar")
        assert d.get_all("Foo") == ["bar"]
