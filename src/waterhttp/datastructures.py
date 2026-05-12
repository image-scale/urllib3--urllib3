from __future__ import annotations

import typing
from collections import OrderedDict
from threading import RLock

_KT = typing.TypeVar("_KT")
_VT = typing.TypeVar("_VT")
_DT = typing.TypeVar("_DT")


class RecentlyUsedContainer(typing.Generic[_KT, _VT], typing.MutableMapping[_KT, _VT]):
    _container: typing.OrderedDict[_KT, _VT]
    _maxsize: int
    dispose_func: typing.Callable[[_VT], None] | None
    lock: RLock

    def __init__(
        self,
        maxsize: int = 10,
        dispose_func: typing.Callable[[_VT], None] | None = None,
    ) -> None:
        super().__init__()
        self._maxsize = maxsize
        self.dispose_func = dispose_func
        self._container = OrderedDict()
        self.lock = RLock()

    def __getitem__(self, key: _KT) -> _VT:
        with self.lock:
            item = self._container.pop(key)
            self._container[key] = item
            return item

    def __setitem__(self, key: _KT, value: _VT) -> None:
        evicted_item = None
        with self.lock:
            try:
                evicted_item = key, self._container.pop(key)
                self._container[key] = value
            except KeyError:
                self._container[key] = value
                if len(self._container) > self._maxsize:
                    evicted_item = self._container.popitem(last=False)

        if evicted_item is not None and self.dispose_func:
            _, evicted_value = evicted_item
            self.dispose_func(evicted_value)

    def __delitem__(self, key: _KT) -> None:
        with self.lock:
            value = self._container.pop(key)
        if self.dispose_func:
            self.dispose_func(value)

    def __len__(self) -> int:
        with self.lock:
            return len(self._container)

    def __iter__(self) -> typing.NoReturn:
        raise NotImplementedError(
            "Iteration over this class is unlikely to be threadsafe."
        )

    def clear(self) -> None:
        with self.lock:
            values = list(self._container.values())
            self._container.clear()
        if self.dispose_func:
            for value in values:
                self.dispose_func(value)

    def keys(self) -> set[_KT]:  # type: ignore[override]
        with self.lock:
            return set(self._container.keys())


class HTTPHeaderDictItemView(set[tuple[str, str]]):
    _headers: HTTPHeaderDict

    def __init__(self, headers: HTTPHeaderDict) -> None:
        self._headers = headers

    def __len__(self) -> int:
        return len(list(self._headers.iteritems()))

    def __iter__(self) -> typing.Iterator[tuple[str, str]]:
        return self._headers.iteritems()

    def __contains__(self, item: object) -> bool:
        if isinstance(item, tuple) and len(item) == 2:
            passed_key, passed_val = item
            if isinstance(passed_key, str) and isinstance(passed_val, str):
                return self._headers._has_value_for_header(passed_key, passed_val)
        return False


class HTTPHeaderDict(typing.MutableMapping[str, str]):
    _container: typing.MutableMapping[str, list[str]]

    def __init__(
        self,
        headers: HTTPHeaderDict | typing.Mapping[str, str] | typing.Iterable[tuple[str, str]] | None = None,
        **kwargs: str,
    ):
        super().__init__()
        self._container = {}
        if headers is not None:
            if isinstance(headers, HTTPHeaderDict):
                self._copy_from(headers)
            else:
                self.extend(headers)
        if kwargs:
            self.extend(kwargs)

    def __setitem__(self, key: str, val: str) -> None:
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        self._container[key.lower()] = [key, val]

    def __getitem__(self, key: str) -> str:
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        val = self._container[key.lower()]
        return ", ".join(val[1:])

    def __delitem__(self, key: str) -> None:
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        del self._container[key.lower()]

    def __contains__(self, key: object) -> bool:
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        if isinstance(key, str):
            return key.lower() in self._container
        return False

    def setdefault(self, key: str, default: str = "") -> str:
        return super().setdefault(key, default)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HTTPHeaderDict):
            other_hd = other
        elif isinstance(other, typing.Mapping):
            other_hd = type(self)(other)
        else:
            return False
        return {k.lower(): v for k, v in self.itermerged()} == {
            k.lower(): v for k, v in other_hd.itermerged()
        }

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __len__(self) -> int:
        return len(self._container)

    def __iter__(self) -> typing.Iterator[str]:
        for vals in self._container.values():
            yield vals[0]

    def discard(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            pass

    def add(self, key: str, val: str, *, combine: bool = False) -> None:
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        key_lower = key.lower()
        new_vals = [key, val]
        vals = self._container.setdefault(key_lower, new_vals)
        if new_vals is not vals:
            if combine:
                vals[-1] = vals[-1] + ", " + val
            else:
                vals.append(val)

    def extend(
        self,
        *args: HTTPHeaderDict | typing.Mapping[str, str] | typing.Iterable[tuple[str, str]],
        **kwargs: str,
    ) -> None:
        if len(args) > 1:
            raise TypeError(
                f"extend() takes at most 1 positional arguments ({len(args)} given)"
            )
        other = args[0] if len(args) >= 1 else ()

        if isinstance(other, HTTPHeaderDict):
            for key, val in other.iteritems():
                self.add(key, val)
        elif isinstance(other, typing.Mapping):
            for key, val in other.items():
                self.add(key, val)
        elif isinstance(other, typing.Iterable):
            for key, value in other:
                self.add(key, value)

        for key, value in kwargs.items():
            self.add(key, value)

    def getlist(self, key: str, default: list[str] | _DT = None) -> list[str] | _DT:  # type: ignore[assignment]
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        try:
            vals = self._container[key.lower()]
        except KeyError:
            if default is None:
                return []
            return default
        else:
            return vals[1:]

    getheaders = getlist
    getallmatchingheaders = getlist
    iget = getlist
    get_all = getlist

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self.itermerged())})"

    def _copy_from(self, other: HTTPHeaderDict) -> None:
        for key in other:
            val = other.getlist(key)
            self._container[key.lower()] = [key, *val]

    def copy(self) -> HTTPHeaderDict:
        clone = type(self)()
        clone._copy_from(self)
        return clone

    def iteritems(self) -> typing.Iterator[tuple[str, str]]:
        for key in self:
            vals = self._container[key.lower()]
            for val in vals[1:]:
                yield vals[0], val

    def itermerged(self) -> typing.Iterator[tuple[str, str]]:
        for key in self:
            val = self._container[key.lower()]
            yield val[0], ", ".join(val[1:])

    def items(self) -> HTTPHeaderDictItemView:  # type: ignore[override]
        return HTTPHeaderDictItemView(self)

    def _has_value_for_header(self, header_name: str, potential_value: str) -> bool:
        if header_name in self:
            return potential_value in self._container[header_name.lower()][1:]
        return False

    def __ior__(self, other: object) -> HTTPHeaderDict:
        if isinstance(other, (HTTPHeaderDict, typing.Mapping)):
            self.extend(other)
            return self
        return NotImplemented

    def __or__(self, other: object) -> HTTPHeaderDict:
        if isinstance(other, (HTTPHeaderDict, typing.Mapping)):
            result = self.copy()
            result.extend(other)
            return result
        return NotImplemented

    def __ror__(self, other: object) -> HTTPHeaderDict:
        if isinstance(other, (HTTPHeaderDict, typing.Mapping)):
            result = type(self)(other)
            result.extend(self)
            return result
        return NotImplemented
