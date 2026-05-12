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
