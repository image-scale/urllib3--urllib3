# Acceptance Criteria

## Tasks 1-6 (completed)

## Task 7: Request Header Utilities and Request Methods Mixin

### Acceptance Criteria
- [ ] make_headers(keep_alive=True) returns {"connection": "keep-alive"}
- [ ] make_headers(accept_encoding=True) returns {"accept-encoding": "gzip,deflate[,br][,zstd]"}
- [ ] make_headers(accept_encoding=["gzip", "br"]) returns {"accept-encoding": "gzip,br"}
- [ ] make_headers(user_agent="Bot/1.0") returns {"user-agent": "Bot/1.0"}
- [ ] make_headers(basic_auth="user:pass") returns {"authorization": "Basic dXNlcjpwYXNz"}
- [ ] make_headers(proxy_basic_auth="user:pass") returns {"proxy-authorization": "Basic dXNlcjpwYXNz"}
- [ ] make_headers(disable_cache=True) returns {"cache-control": "no-cache"}
- [ ] body_to_chunks with bytes body returns chunks with correct content_length
- [ ] body_to_chunks with None body returns None chunks
- [ ] body_to_chunks with file-like body returns iterable chunks
- [ ] RequestMethods mixin provides request(), get(), post(), put(), delete(), etc.
- [ ] request() routes GET/HEAD/DELETE to URL-encoded fields
- [ ] request() routes POST/PUT/PATCH to body-encoded fields
- [ ] request() handles JSON encoding when json parameter provided
- [ ] request_encode_body() uses multipart encoding by default
