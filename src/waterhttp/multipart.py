from __future__ import annotations

import binascii
import codecs
import mimetypes
import os
import typing


def guess_content_type(filename: str | None, default: str = "application/octet-stream") -> str:
    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            return guessed
    return default


def format_multipart_header_param(name: str, value: str | bytes) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    value = value.replace("\r", "%0D").replace("\n", "%0A").replace('"', "%22")
    return f'{name}="{value}"'


class FormField:
    def __init__(
        self,
        name: str,
        data: str | bytes,
        filename: str | None = None,
        headers: dict[str, str] | None = None,
        header_formatter: typing.Callable[[str, str | bytes], str] | None = None,
    ) -> None:
        self._name = name
        self._filename = filename
        self.data = data
        self.headers = headers or {}
        self._header_formatter = header_formatter or format_multipart_header_param

    @classmethod
    def from_tuples(
        cls,
        fieldname: str,
        value: str | bytes | tuple[str, str | bytes] | tuple[str, str | bytes, str],
        header_formatter: typing.Callable[[str, str | bytes], str] | None = None,
    ) -> FormField:
        filename: str | None = None
        content_type: str | None = None
        data: str | bytes

        if isinstance(value, tuple):
            if len(value) == 3:
                filename, data, content_type = value  # type: ignore[misc]
            elif len(value) == 2:
                filename, data = value  # type: ignore[misc]
            else:
                raise ValueError(f"Invalid field tuple length: {len(value)}")
        else:
            data = value

        field = cls(name=fieldname, data=data, filename=filename, header_formatter=header_formatter)
        field.make_multipart(content_type=content_type)
        return field

    def _render_part(self, name: str, value: str | bytes) -> str:
        return self._header_formatter(name, value)

    def _render_parts(self, header_parts: dict[str, str | bytes | None]) -> str:
        parts = []
        for name, value in header_parts.items():
            if value is not None:
                parts.append(self._render_part(name, value))
        return "; ".join(parts)

    def make_multipart(
        self,
        content_disposition: str = "form-data",
        content_type: str | None = None,
        content_location: str | None = None,
    ) -> None:
        disposition_params: dict[str, str | bytes | None] = {"name": self._name}
        if self._filename is not None:
            disposition_params["filename"] = self._filename

        self.headers["Content-Disposition"] = (
            content_disposition + "; " + self._render_parts(disposition_params)
        )

        if content_type is None and self._filename is not None:
            content_type = guess_content_type(self._filename)

        if content_type:
            self.headers["Content-Type"] = content_type

        if content_location:
            self.headers["Content-Location"] = content_location

    def render_headers(self) -> str:
        lines = []
        header_order = ["Content-Disposition", "Content-Type", "Content-Location"]
        for header_name in header_order:
            if header_name in self.headers:
                lines.append(f"{header_name}: {self.headers[header_name]}\r\n")
        for header_name, header_value in self.headers.items():
            if header_name not in header_order:
                lines.append(f"{header_name}: {header_value}\r\n")
        lines.append("\r\n")
        return "".join(lines)


def choose_boundary() -> str:
    return binascii.hexlify(os.urandom(16)).decode()


def iter_field_objects(
    fields: typing.Mapping[str, str | bytes | tuple[str, str | bytes] | tuple[str, str | bytes, str]]
    | typing.Sequence[tuple[str, str | bytes | tuple[str, str | bytes] | tuple[str, str | bytes, str]] | FormField],
) -> typing.Iterator[FormField]:
    if isinstance(fields, typing.Mapping):
        for name, value in fields.items():
            yield FormField.from_tuples(name, value)
    else:
        for item in fields:
            if isinstance(item, FormField):
                yield item
            else:
                name, value = item
                yield FormField.from_tuples(name, value)


def encode_multipart_formdata(
    fields: typing.Mapping[str, str | bytes | tuple[str, str | bytes] | tuple[str, str | bytes, str]]
    | typing.Sequence[tuple[str, str | bytes | tuple[str, str | bytes] | tuple[str, str | bytes, str]] | FormField],
    boundary: str | None = None,
) -> tuple[bytes, str]:
    if boundary is None:
        boundary = choose_boundary()

    body = bytearray()
    for field in iter_field_objects(fields):
        body.extend(f"--{boundary}\r\n".encode())
        header_str = field.render_headers()
        body.extend(header_str.encode("utf-8"))
        data = field.data
        if isinstance(data, str):
            data = data.encode("utf-8")
        body.extend(data)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())

    content_type = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type
