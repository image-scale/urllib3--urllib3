# Progress

## Round 1
**Task**: Task 1 — URL parsing with normalization, IPv6, dot-segment removal, and error handling
**Files created**: src/waterhttp/__init__.py, src/waterhttp/exceptions.py, src/waterhttp/url.py, tests/test_url.py
**Commit**: Add URL parsing that breaks a URL string into scheme, auth, host, port, path, query, and fragment components.
**Acceptance**: 19/19 criteria met
**Verification**: tests FAIL on previous state (patch doesn't apply), PASS on current state

## Round 2
**Task**: Task 2 — Timeout configuration with connect/read/total timeouts
**Files created**: src/waterhttp/timeout.py, tests/test_timeout.py
**Commit**: Add timeout configuration supporting connect, read, and total timeouts.
**Acceptance**: 18/18 criteria met
**Verification**: tests FAIL on previous state (patch doesn't apply), PASS on current state

## Round 3
**Task**: Task 3 — Retry logic with per-error-type counting, backoff, and history
**Files created**: src/waterhttp/retry.py, tests/test_retry.py
**Commit**: Add retry logic that tracks retry counts per error type.
**Acceptance**: 21/21 criteria met
**Verification**: tests FAIL on previous state (patch doesn't apply), PASS on current state

## Round 4
**Task**: Task 4+5 — HTTPHeaderDict and RecentlyUsedContainer
**Files created**: src/waterhttp/datastructures.py, tests/test_datastructures.py
**Commit**: Add case-insensitive HTTP header dict and LRU container.
**Acceptance**: 24/24 criteria met
**Verification**: tests FAIL on previous state (patch doesn't apply), PASS on current state
