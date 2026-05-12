# Acceptance Criteria

## Task 1: URL Parsing (completed)

## Task 2: Timeout Configuration

### Acceptance Criteria
- [ ] Timeout(total=5) creates a timeout with total=5, connect and read as default sentinel
- [ ] Timeout(connect=3, read=10) stores individual timeouts
- [ ] Timeout.from_float(5) creates Timeout with connect=read=5
- [ ] Timeout.from_float(None) creates Timeout with connect=read=None (no timeout)
- [ ] clone() returns an independent copy with same configuration
- [ ] start_connect() records start time and returns it
- [ ] start_connect() raises error if called twice without cloning
- [ ] get_connect_duration() returns elapsed time since start_connect
- [ ] connect_timeout property returns connect value when no total set
- [ ] connect_timeout returns min(total, connect) when both set
- [ ] read_timeout returns read value when no total set
- [ ] read_timeout adjusts for time spent connecting when total is set (total - elapsed)
- [ ] read_timeout raises error if total set but connect never started
- [ ] Negative timeout values raise ValueError
- [ ] Boolean values (True/False) raise ValueError
- [ ] String values raise ValueError
- [ ] None is a valid timeout value (means no timeout)
- [ ] resolve_default_timeout returns socket default when sentinel passed
