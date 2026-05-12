# Acceptance Criteria

## Task 1: URL Parsing (completed)
## Task 2: Timeout Configuration (completed)

## Task 3: Retry Logic

### Acceptance Criteria
- [ ] Retry(total=3) creates retry allowing 3 total retries
- [ ] Retry() defaults total to 10
- [ ] increment() decrements total and returns new Retry instance
- [ ] increment() raises MaxRetryError when retries exhausted (total goes below 0)
- [ ] connect retries: increment(error=ConnectTimeoutError()) decrements connect count
- [ ] read retries: increment(error=ReadTimeoutError()) decrements read count
- [ ] redirect retries: increment with response having redirect decrements redirect count
- [ ] status retries: increment with status code in status_forcelist decrements status count
- [ ] get_backoff_time() returns 0 for first retry, then factor * 2^(n-1) for subsequent
- [ ] backoff_max caps the backoff time
- [ ] from_int(3) creates Retry(total=3)
- [ ] from_int(Retry(...)) returns the Retry object unchanged
- [ ] from_int(None) returns Retry.DEFAULT
- [ ] is_retry(method, status_code) returns True if method allowed and status in forcelist
- [ ] allowed_methods restricts which HTTP methods can be retried
- [ ] history tracks each retry attempt as RequestHistory entries
- [ ] new() creates copy with updated parameters
- [ ] Retry.DEFAULT is a class-level default retry configuration
- [ ] raise_on_redirect=True raises MaxRetryError on redirect exhaustion
- [ ] parse_retry_after("120") returns 120.0
- [ ] is_exhausted() returns True when any count goes below 0
