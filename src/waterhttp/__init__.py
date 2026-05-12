from __future__ import annotations

import logging
import typing
import warnings
from logging import NullHandler

from . import exceptions
from .connectionpool import HTTPPool, HTTPSPool, connection_from_url
from .datastructures import HTTPHeaderDict
from .multipart import encode_multipart_formdata
from .poolmanager import PoolManager, ProxyManager, proxy_from_url
from .request_helpers import make_headers
from .response import BaseHTTPResponse, WaterHTTPResponse
from .retry import Retry
from .timeout import Timeout
from .url import Url, parse_url
from .exceptions import HTTPError, HTTPWarning, LocationParseError, LocationValueError

__all__ = (
    "HTTPPool",
    "HTTPSPool",
    "HTTPHeaderDict",
    "PoolManager",
    "ProxyManager",
    "WaterHTTPResponse",
    "BaseHTTPResponse",
    "Retry",
    "Timeout",
    "Url",
    "add_stderr_logger",
    "connection_from_url",
    "disable_warnings",
    "encode_multipart_formdata",
    "make_headers",
    "parse_url",
    "proxy_from_url",
    "request",
)

logging.getLogger(__name__).addHandler(NullHandler())


def add_stderr_logger(
    level: int = logging.DEBUG,
) -> logging.StreamHandler[typing.TextIO]:
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.debug("Added a stderr logging handler to logger: %s", __name__)
    return handler


del NullHandler

warnings.simplefilter("always", exceptions.SecurityWarning, append=True)
warnings.simplefilter("default", exceptions.InsecurePlatformWarning, append=True)


def disable_warnings(category: type[Warning] = exceptions.HTTPWarning) -> None:
    warnings.simplefilter("ignore", category)


_DEFAULT_POOL = PoolManager()


def request(
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    fields: typing.Mapping[str, str] | typing.Sequence[tuple[str, str]] | None = None,
    headers: typing.Mapping[str, str] | None = None,
    preload_content: bool | None = True,
    decode_content: bool | None = True,
    redirect: bool | None = True,
    retries: Retry | bool | int | None = None,
    timeout: Timeout | float | int | None = 3,
    json: typing.Any | None = None,
) -> BaseHTTPResponse:
    return _DEFAULT_POOL.request(
        method,
        url,
        body=body,
        fields=fields,
        headers=headers,
        preload_content=preload_content,
        decode_content=decode_content,
        redirect=redirect,
        retries=retries,
        timeout=timeout,
        json=json,
    )
