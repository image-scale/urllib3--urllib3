# Acceptance Criteria

## Tasks 1-7 (completed)

## Task 8: HTTP/HTTPS Connection Classes

### Acceptance Criteria
- [ ] HTTPConnection wraps http.client.HTTPConnection with default port 80
- [ ] HTTPSConnection extends HTTPConnection with default port 443 and SSL
- [ ] Connections accept host, port, timeout, source_address, blocksize, socket_options
- [ ] Default socket options include TCP_NODELAY
- [ ] set_tunnel(host, port, headers, scheme) configures proxy tunneling
- [ ] is_closed, is_connected properties report connection state
- [ ] SSL context creation with configurable minimum/maximum TLS versions
- [ ] Certificate verification enabled by default
- [ ] assert_fingerprint verifies certificate SHA-256 fingerprint
- [ ] create_ssl_context() produces a secure SSL context with safe defaults
- [ ] port_by_scheme maps "http" to 80 and "https" to 443
- [ ] is_connection_dropped() detects closed connections
- [ ] Connection creates socket with given socket_options and timeout
