# Goal

## Project
urllib3 — a python project.

## Description
A feature-rich HTTP client library for Python providing connection pooling, retry logic, SSL/TLS verification, content decompression, multipart file uploads, proxy support, and timeout management. It offers a high-level PoolManager for managing multiple connection pools, a Retry mechanism with backoff, and a full-featured HTTPResponse with automatic content decoding.

## Scope
- ~15 production source files to implement
- ~12 test files to write
- Reproduce all core source code, tests, and configuration

## Core Capabilities
1. URL parsing with RFC 3986 compliance, IPv6 support, and normalization
2. Timeout configuration with connect/read/total timeout management
3. Retry logic with exponential backoff, redirect tracking, and per-error-type counting
4. Case-insensitive HTTP header dictionary with duplicate header support
5. LRU container for connection pool caching
6. Multipart form-data encoding with file upload support
7. Exception hierarchy covering pool, connection, timeout, SSL, proxy, and protocol errors
8. HTTP request method routing (URL-encoded vs body-encoded based on method)
9. HTTP/HTTPS connection classes with socket options, proxy tunneling, and SSL configuration
10. Connection pooling with LIFO queue, connection reuse, and health checks
11. Pool manager with LRU-based multi-host pool management
12. HTTP response with streaming, content decompression (gzip, deflate, brotli, zstd), and JSON support
13. SSL/TLS context creation, certificate verification, and fingerprint assertion
14. Convenience top-level request function
15. Request header utilities (make_headers, basic auth, accept-encoding)
