# Acceptance Criteria

## Task 1: URL Parsing (completed)
## Task 2: Timeout Configuration (completed)
## Task 3: Retry Logic (completed)

## Task 4: HTTP Header Dictionary and LRU Container

### Acceptance Criteria
- [ ] HTTPHeaderDict stores headers case-insensitively: d["Content-Type"] == d["content-type"]
- [ ] __setitem__ overwrites existing values for the same key (case-insensitive)
- [ ] __getitem__ returns comma-joined values when multiple values exist
- [ ] add(key, val) appends value without overwriting
- [ ] add(key, val, combine=True) appends to last value with ", "
- [ ] getlist(key) returns list of all values for a key
- [ ] getlist returns empty list for missing key
- [ ] iteritems() yields all (key, val) pairs including duplicates
- [ ] itermerged() yields merged pairs with comma-separated values
- [ ] copy() returns deep copy that is independent
- [ ] __eq__ compares case-insensitively
- [ ] extend() adds from dict, iterable of pairs, or another HTTPHeaderDict
- [ ] __contains__ is case-insensitive
- [ ] | operator merges two header dicts
- [ ] |= operator extends in-place
- [ ] __len__ returns number of unique keys
- [ ] __iter__ yields original-cased key names
- [ ] RecentlyUsedContainer evicts LRU item when maxsize exceeded
- [ ] __getitem__ marks item as recently used
- [ ] dispose_func called on eviction
- [ ] clear() disposes all items
- [ ] Thread-safe via locking
- [ ] __iter__ raises NotImplementedError
- [ ] keys() returns set of keys
