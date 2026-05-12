# Todo

## Plan
Build the HTTP client library top-down, starting with the most important user-facing feature (making HTTP requests via a pool manager), then adding supporting features. Infrastructure like exceptions and utilities are created alongside the first feature that needs them. Each task delivers a complete, testable capability.

## Tasks
- [x] Task 1: Implement URL parsing that breaks a URL string into components (scheme, auth, host, port, path, query, fragment) with proper normalization, IPv6 support, and URL reconstruction. Include error handling for invalid URLs.
- [x] Task 2: Implement timeout configuration that supports connect, read, and total timeouts with dynamic remaining-time calculation, duration tracking, and cloning for per-request use.
- [x] Task 3: Implement retry logic that tracks retry counts per error type (connect, read, redirect, status), supports exponential backoff with configurable factor, maintains request history, and raises when retries are exhausted.
- [x] Task 4: Implement a case-insensitive HTTP header dictionary and an LRU container. (Combined with Task 5)
- [x] Task 5: (Merged into Task 4)
- [x] Task 6: Implement multipart form-data encoding that takes form fields (strings, files with filenames and content types) and produces a properly formatted multipart body with boundary, content-disposition headers, and MIME type guessing.
- [x] Task 7: Implement request header utilities including a make_headers function that generates common HTTP headers (keep-alive, accept-encoding, user-agent, basic auth, proxy auth, cache control), and body chunking for file-like objects and iterables.
- [x] Task 8: Implement HTTP/HTTPS connection classes that wrap Python's http.client with configurable socket options, timeout handling, proxy tunneling via CONNECT, and SSL/TLS with certificate verification, hostname checking, and fingerprint assertion.
- [x] Task 9: Implement connection pooling that manages a LIFO queue of reusable connections per host, with configurable pool size, blocking/non-blocking get, connection health checks, and automatic connection creation.
- [x] Task 10: Implement an HTTP response class that wraps raw responses, supports streaming reads, automatic content decompression (gzip, deflate, brotli, zstd), JSON parsing, content-length enforcement, and chunked transfer decoding.
- [x] Task 11: Implement a pool manager that maintains an LRU cache of connection pools keyed by (scheme, host, port), routes requests to the correct pool, follows redirects across hosts, and supports proxy configuration.
- [x] Task 12: Implement a top-level convenience API with a module-level request function, public exports of all major classes, and helper functions like connection_from_url and proxy_from_url.
