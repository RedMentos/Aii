# G13 EventScheduler timing admission — preregistration 2026-10-29

Parent checkpoint `f7dc3b7820a7365a7c4cd6f12ccd2afe5c2c519a`.
Independent G13 boundary beyond SleepRuntime user-delay fix.

## Failure mode
`EventScheduler._post` currently validates event kind/origin/action,
then may evict a lower-priority pending event before converting `due` and
`ttl` to floats. Nonfinite `due` or `ttl` is not valid durable timing
evidence; invalid inputs must be refused **before** dedup, capacity eviction,
sequence increment or Store mutation. Preserve existing valid scheduling
and retry/burnout/age behavior. No new scheduler action or authority.

## Frozen tests
- NaN/±Inf `due`, NaN/±Inf/negative `ttl`, and a finite TTL whose
  `clock()+ttl` overflows: ValueError; queue/state unchanged.
- Nonfinite scheduler clock: refuse before publication.
- At MAX_PENDING=1, an invalid high-priority event must not evict the
  existing lower-priority pending event.
- Finite due/TTL USER timer still posts and expires per existing rules.
- Existing scheduler and Sleep tests pass, no native/model calls.
- CI Canon blob, focused software tests, privacy/diff/compile, closed raw
  SHA256SUMS, no STEP2/B3/Body-JEPA/LP3/World-JEPA/Redmi gate promotion.
