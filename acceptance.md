# Acceptance Criteria

## Tasks 1-5 (completed)

## Task 6: Multipart Form-Data Encoding

### Acceptance Criteria
- [ ] encode_multipart_formdata({"key": "value"}) returns (body_bytes, content_type_string)
- [ ] Content-type includes the boundary string
- [ ] Body contains --boundary before each field and --boundary-- at the end
- [ ] Fields support string values: {"name": "John"} encodes name=John
- [ ] Fields support file tuples: {"file": ("name.txt", b"content")} includes filename
- [ ] Fields support file tuples with MIME type: {"file": ("name.txt", b"data", "text/plain")}
- [ ] MIME type is guessed from filename (e.g., "image.jpg" → "image/jpeg")
- [ ] Default MIME type is "application/octet-stream" for unknown extensions
- [ ] Both dict and list-of-tuples input formats are supported
- [ ] RequestField.render_headers() produces Content-Disposition with name and filename
- [ ] Boundary is randomly generated when not provided
- [ ] Custom boundary can be passed
- [ ] Body bytes are properly CRLF-separated
