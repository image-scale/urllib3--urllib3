from __future__ import annotations

import io
import typing
from base64 import b64encode

from .exceptions import UnrewindableBodyError

SKIP_HEADER = "@@@SKIP_HEADER@@@"
SKIPPABLE_HEADERS = frozenset(["accept-encoding", "host", "user-agent"])

ACCEPT_ENCODING = "gzip,deflate"
try:
    try:
        import brotlicffi as _unused_brotli  # noqa: F401
    except ImportError:
        import brotli as _unused_brotli  # noqa: F401
except ImportError:
    pass
else:
    ACCEPT_ENCODING += ",br"

try:
    import sys
    if sys.version_info >= (3, 14):
        from compression import zstd as _unused_zstd  # noqa: F401
    else:
        from backports import zstd as _unused_zstd  # noqa: F401
except ImportError:
    pass
else:
    ACCEPT_ENCODING += ",zstd"


_METHODS_NOT_EXPECTING_BODY = {"GET", "HEAD", "DELETE", "TRACE", "OPTIONS", "CONNECT"}


def _to_bytes(x: str | bytes) -> bytes:
    if isinstance(x, bytes):
        return x
    return x.encode("utf-8")


def make_headers(
    keep_alive: bool | None = None,
    accept_encoding: bool | list[str] | str | None = None,
    user_agent: str | None = None,
    basic_auth: str | None = None,
    proxy_basic_auth: str | None = None,
    disable_cache: bool | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}

    if accept_encoding:
        if isinstance(accept_encoding, str):
            pass
        elif isinstance(accept_encoding, list):
            accept_encoding = ",".join(accept_encoding)
        else:
            accept_encoding = ACCEPT_ENCODING
        headers["accept-encoding"] = accept_encoding

    if user_agent:
        headers["user-agent"] = user_agent

    if keep_alive:
        headers["connection"] = "keep-alive"

    if basic_auth:
        headers["authorization"] = (
            f"Basic {b64encode(basic_auth.encode('latin-1')).decode()}"
        )

    if proxy_basic_auth:
        headers["proxy-authorization"] = (
            f"Basic {b64encode(proxy_basic_auth.encode('latin-1')).decode()}"
        )

    if disable_cache:
        headers["cache-control"] = "no-cache"

    return headers


def rewind_body(body: typing.IO[typing.AnyStr], body_pos: int) -> None:
    body_seek = getattr(body, "seek", None)
    if body_seek is not None and isinstance(body_pos, int):
        try:
            body_seek(body_pos)
        except OSError as e:
            raise UnrewindableBodyError(
                "An error occurred when rewinding request body for redirect/retry."
            ) from e
    else:
        raise ValueError(
            f"body_pos must be of type integer, instead it was {type(body_pos)}."
        )


class ChunksAndContentLength(typing.NamedTuple):
    chunks: typing.Iterable[bytes] | None
    content_length: int | None


def body_to_chunks(
    body: typing.Any | None, method: str, blocksize: int
) -> ChunksAndContentLength:
    chunks: typing.Iterable[bytes] | None
    content_length: int | None

    if body is None:
        chunks = None
        if method.upper() not in _METHODS_NOT_EXPECTING_BODY:
            content_length = 0
        else:
            content_length = None

    elif isinstance(body, (str, bytes)):
        chunks_data = (_to_bytes(body),)
        chunks = chunks_data
        content_length = len(chunks_data[0])

    elif hasattr(body, "read"):
        def chunk_readable() -> typing.Iterable[bytes]:
            encode = isinstance(body, io.TextIOBase)
            while True:
                datablock = body.read(blocksize)
                if not datablock:
                    break
                if encode:
                    datablock = datablock.encode("utf-8")
                yield datablock

        chunks = chunk_readable()
        content_length = None

    else:
        try:
            mv = memoryview(body)
        except TypeError:
            try:
                chunks = iter(body)
                content_length = None
            except TypeError:
                raise TypeError(
                    f"'body' must be a bytes-like object, file-like "
                    f"object, or iterable. Instead was {body!r}"
                ) from None
        else:
            chunks = (body,)
            content_length = mv.nbytes

    return ChunksAndContentLength(chunks=chunks, content_length=content_length)
