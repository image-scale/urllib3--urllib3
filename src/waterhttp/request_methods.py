from __future__ import annotations

import json as _json
import typing
from urllib.parse import urlencode

from .datastructures import HTTPHeaderDict
from .multipart import encode_multipart_formdata

if typing.TYPE_CHECKING:
    from .response import BaseHTTPResponse


class RequestMethods:
    _encode_url_methods = {"DELETE", "GET", "HEAD", "OPTIONS"}

    def __init__(self, headers: typing.Mapping[str, str] | None = None) -> None:
        self.headers = headers or {}

    def urlopen(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: typing.Mapping[str, str] | None = None,
        encode_multipart: bool = True,
        multipart_boundary: str | None = None,
        **kw: typing.Any,
    ) -> BaseHTTPResponse:
        raise NotImplementedError(
            "Classes using RequestMethods must implement urlopen"
        )

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        fields: (
            typing.Mapping[str, str]
            | typing.Sequence[tuple[str, str]]
            | None
        ) = None,
        headers: typing.Mapping[str, str] | None = None,
        json: typing.Any = None,
        **urlopen_kw: typing.Any,
    ) -> BaseHTTPResponse:
        if json is not None:
            if body is not None:
                raise TypeError(
                    "request got values for both 'body' and 'json' parameters which are mutually exclusive"
                )
            body = _json.dumps(json).encode("utf-8")
            if headers is None:
                headers = {"Content-Type": "application/json"}
            else:
                headers = HTTPHeaderDict(headers)
                headers.setdefault("Content-Type", "application/json")

        if method.upper() in self._encode_url_methods:
            return self.request_encode_url(
                method, url, fields=fields, headers=headers, **urlopen_kw
            )
        else:
            return self.request_encode_body(
                method, url, fields=fields, headers=headers, body=body, **urlopen_kw
            )

    def request_encode_url(
        self,
        method: str,
        url: str,
        fields: (
            typing.Mapping[str, str]
            | typing.Sequence[tuple[str, str]]
            | None
        ) = None,
        headers: typing.Mapping[str, str] | None = None,
        **urlopen_kw: typing.Any,
    ) -> BaseHTTPResponse:
        if fields:
            url += "?" + urlencode(fields)
        return self.urlopen(method, url, headers=headers, **urlopen_kw)

    def request_encode_body(
        self,
        method: str,
        url: str,
        fields: (
            typing.Mapping[str, str]
            | typing.Sequence[tuple[str, str]]
            | None
        ) = None,
        headers: typing.Mapping[str, str] | None = None,
        encode_multipart: bool = True,
        multipart_boundary: str | None = None,
        body: bytes | None = None,
        **urlopen_kw: typing.Any,
    ) -> BaseHTTPResponse:
        if fields:
            if encode_multipart:
                body_bytes, content_type = encode_multipart_formdata(
                    fields, boundary=multipart_boundary
                )
                body = body_bytes
            else:
                body = urlencode(fields).encode("utf-8")  # type: ignore[arg-type]
                content_type = "application/x-www-form-urlencoded"

            if headers is None:
                headers = {"Content-Type": content_type}
            else:
                headers = HTTPHeaderDict(headers)
                headers.setdefault("Content-Type", content_type)

        return self.urlopen(method, url, body=body, headers=headers, **urlopen_kw)

    def get(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("POST", url, **kw)

    def put(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("PUT", url, **kw)

    def patch(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("PATCH", url, **kw)

    def delete(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("DELETE", url, **kw)

    def head(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("HEAD", url, **kw)

    def options(self, url: str, **kw: typing.Any) -> BaseHTTPResponse:
        return self.request("OPTIONS", url, **kw)
