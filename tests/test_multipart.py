from __future__ import annotations

import pytest

from waterhttp.multipart import (
    FormField,
    choose_boundary,
    encode_multipart_formdata,
    guess_content_type,
    format_multipart_header_param,
)


BOUNDARY = "testboundary123"
BOUNDARY_BYTES = BOUNDARY.encode()


class TestGuessContentType:
    @pytest.mark.parametrize("filename, expected", [
        ("image.jpg", "image/jpeg"),
        ("doc.pdf", "application/pdf"),
        ("page.html", "text/html"),
        ("unknown.qwertyasdf", "application/octet-stream"),
        (None, "application/octet-stream"),
    ])
    def test_content_type_guessing(self, filename, expected):
        result = guess_content_type(filename)
        if filename == "image.jpg":
            assert result in ("image/jpeg", "image/pjpeg")
        else:
            assert result == expected


class TestFormatMultipartHeaderParam:
    def test_simple_string(self):
        result = format_multipart_header_param("name", "value")
        assert result == 'name="value"'

    def test_quotes_escaped(self):
        result = format_multipart_header_param("name", 'val"ue')
        assert result == 'name="val%22ue"'

    def test_newlines_escaped(self):
        result = format_multipart_header_param("name", "val\nue")
        assert result == 'name="val%0Aue"'

    def test_bytes_value(self):
        result = format_multipart_header_param("name", b"value")
        assert result == 'name="value"'


class TestFormField:
    def test_from_tuples_string(self):
        field = FormField.from_tuples("key", "value")
        assert field._name == "key"
        assert field.data == "value"
        assert field._filename is None

    def test_from_tuples_file(self):
        field = FormField.from_tuples("file", ("test.txt", b"content"))
        assert field._name == "file"
        assert field._filename == "test.txt"
        assert field.data == b"content"

    def test_from_tuples_file_with_mime(self):
        field = FormField.from_tuples("file", ("test.txt", b"data", "text/plain"))
        assert field.headers["Content-Type"] == "text/plain"

    def test_render_headers(self):
        field = FormField.from_tuples("name", "value")
        headers = field.render_headers()
        assert "Content-Disposition: form-data" in headers
        assert 'name="name"' in headers
        assert headers.endswith("\r\n\r\n")

    def test_render_headers_with_filename(self):
        field = FormField.from_tuples("file", ("photo.jpg", b"data"))
        headers = field.render_headers()
        assert 'filename="photo.jpg"' in headers
        assert "Content-Type:" in headers

    def test_make_multipart_auto_mime(self):
        field = FormField(name="file", data=b"data", filename="doc.pdf")
        field.make_multipart()
        assert field.headers["Content-Type"] == "application/pdf"


class TestEncodeMultipart:
    def test_simple_fields(self):
        body, content_type = encode_multipart_formdata(
            {"key": "value"}, boundary=BOUNDARY
        )
        assert content_type == f"multipart/form-data; boundary={BOUNDARY}"
        assert BOUNDARY_BYTES in body
        assert b"key" in body
        assert b"value" in body

    def test_boundary_markers(self):
        body, _ = encode_multipart_formdata(
            {"k": "v"}, boundary=BOUNDARY
        )
        assert body.count(f"--{BOUNDARY}".encode()) == 2
        assert body.endswith(f"--{BOUNDARY}--\r\n".encode())

    @pytest.mark.parametrize("fields", [
        {"k": "v", "k2": "v2"},
        [("k", "v"), ("k2", "v2")],
    ])
    def test_dict_and_list_input(self, fields):
        body, _ = encode_multipart_formdata(fields, boundary=BOUNDARY)
        assert body.count(BOUNDARY_BYTES) == 3

    def test_file_upload(self):
        fields = {"file": ("test.txt", b"file content", "text/plain")}
        body, content_type = encode_multipart_formdata(fields, boundary=BOUNDARY)
        assert b"file content" in body
        assert b'filename="test.txt"' in body
        assert b"Content-Type: text/plain" in body

    def test_file_without_mime(self):
        fields = {"file": ("photo.jpg", b"jpeg data")}
        body, _ = encode_multipart_formdata(fields, boundary=BOUNDARY)
        assert b'filename="photo.jpg"' in body
        assert b"Content-Type: image/" in body

    def test_auto_boundary(self):
        body, content_type = encode_multipart_formdata({"k": "v"})
        assert "multipart/form-data; boundary=" in content_type
        boundary = content_type.split("boundary=")[1]
        assert len(boundary) == 32

    def test_mixed_string_and_file(self):
        fields = [
            ("name", "John"),
            ("file", ("doc.txt", b"content", "text/plain")),
        ]
        body, _ = encode_multipart_formdata(fields, boundary=BOUNDARY)
        assert b"John" in body
        assert b"content" in body
        assert b'filename="doc.txt"' in body

    def test_bytes_field_value(self):
        body, _ = encode_multipart_formdata({"key": b"bytes_val"}, boundary=BOUNDARY)
        assert b"bytes_val" in body

    def test_choose_boundary_unique(self):
        b1 = choose_boundary()
        b2 = choose_boundary()
        assert b1 != b2
        assert len(b1) == 32

    def test_crlf_separation(self):
        body, _ = encode_multipart_formdata({"k": "v"}, boundary=BOUNDARY)
        assert b"\r\n" in body
