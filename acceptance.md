# Acceptance Criteria

## Tasks 1-8 (completed)

## Task 9: Connection Pooling

### Acceptance Criteria
- [x] HTTPPool manages a LIFO queue of connections for a single (host, port)
- [x] HTTPSPool extends HTTPPool with SSL/TLS connection support
- [x] Pool creates new connections on demand when queue is empty
- [x] Pool returns connections to queue after use (via _return_conn)
- [x] Pool has configurable maxsize for the number of pooled connections
- [x] block=True causes _get_conn to wait when pool is empty instead of creating new connection
- [x] Excess connections are closed when returned to a full pool
- [x] close() closes all pooled connections
- [x] is_same_host() compares (scheme, host, port) against pool's target
- [x] connection_from_url() creates appropriate pool from URL string
- [x] Pool is a context manager (__enter__/__exit__)
- [x] EmptyPoolError raised when block=True and pool exhausted with timeout
- [x] num_connections tracks how many connections were created
- [x] Host normalization preserves IPv6 bracket format

## Task 10: HTTP Response

### Acceptance Criteria
- [x] WaterHTTPResponse wraps raw httplib responses via from_httplib()
- [x] Supports preload_content and lazy reading
- [x] read() with amt, decode_content, cache_content parameters
- [x] read1() for single-buffer reads
- [x] stream() generator for chunked iteration
- [x] Automatic gzip decompression
- [x] Automatic deflate decompression (both RFC 1950 and raw RFC 1951)
- [x] Automatic brotli decompression (when available)
- [x] Automatic zstd decompression (when available)
- [x] JSON parsing via json() method
- [x] Content-Length enforcement raises IncompleteRead/ProtocolError
- [x] Redirect detection via get_redirect_location()
- [x] BytesQueueBuffer for memory-efficient partial reads
- [x] Content decoders: GzipDecoder, DeflateDecoder, BrotliDecoder, ZstdDecoder
- [x] Properties: data, url, closed, connection, headers
- [x] Context methods: close(), release_conn(), drain_conn()
- [x] io.IOBase compatibility: readable(), readinto(), fileno()
- [x] Line iteration via __iter__

## Task 11: Pool Manager

### Acceptance Criteria
- [x] PoolManager maintains LRU cache of connection pools keyed by (scheme, host, port)
- [x] Same URL reuses same pool
- [x] Different hosts/schemes/ports get different pools
- [x] LRU eviction when num_pools exceeded
- [x] connection_from_url() creates pool from URL
- [x] connection_from_host() creates pool from host/port/scheme
- [x] clear() empties pool cache
- [x] Context manager support
- [x] SSL keywords stripped for HTTP pools
- [x] SSL keywords preserved for HTTPS pools
- [x] Pool kwargs forwarded to pools
- [x] ProxyManager routes HTTP through proxy
- [x] ProxyManager creates direct pools for HTTPS
- [x] ProxyManager sets proxy headers
- [x] proxy_from_url() factory function
- [x] Unknown scheme raises URLSchemeUnknown
- [x] No host raises LocationValueError

## Task 12: Top-Level Convenience API

### Acceptance Criteria
- [x] Module-level request() function using default PoolManager
- [x] All major classes exported from package __init__
- [x] connection_from_url() accessible at top level
- [x] proxy_from_url() accessible at top level
- [x] make_headers() accessible at top level
- [x] encode_multipart_formdata() accessible at top level
- [x] add_stderr_logger() for debug logging
- [x] disable_warnings() for suppressing warnings
- [x] __all__ contains all public names
- [x] Exception classes exported
