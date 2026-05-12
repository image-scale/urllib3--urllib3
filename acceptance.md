# Acceptance Criteria

## Task 1: URL Parsing

### Acceptance Criteria
- [ ] parse_url("http://google.com/mail") returns Url with scheme="http", host="google.com", path="/mail"
- [ ] parse_url("http://user:pass@host.com:8080/path?q=1#frag") parses all components correctly
- [ ] parse_url("google.com/mail") returns host=None, path="google.com/mail" (no scheme = no host)
- [ ] parse_url("http://google.com/") returns path="/"
- [ ] parse_url("http://google.com") returns path=None
- [ ] Port is returned as integer, e.g., parse_url("http://host:8080/") has port=8080
- [ ] Scheme is lowercased: parse_url("HTTP://host/") returns scheme="http"
- [ ] IPv6 addresses are preserved: parse_url("http://[::1]/") returns host="[::1]"
- [ ] IPv6 with port: parse_url("http://[::1]:8080/") returns host="[::1]", port=8080
- [ ] request_uri property returns path with query: Url(path="/path", query="q=1").request_uri == "/path?q=1"
- [ ] request_uri defaults to "/" when path is None
- [ ] netloc returns "host:port" when port exists, just "host" otherwise
- [ ] url property reconstructs the full URL string from components
- [ ] LocationParseError raised for invalid port (e.g., parse_url("http://host:abc/"))
- [ ] LocationParseError raised for negative port (e.g., parse_url("http://host:-1/"))
- [ ] LocationParseError raised for port > 65535
- [ ] Empty string returns Url with all None fields
- [ ] parse_url handles URLs with only scheme: parse_url("http://") returns scheme="http"
- [ ] Host is lowercased for normalization
