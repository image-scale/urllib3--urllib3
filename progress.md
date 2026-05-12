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
