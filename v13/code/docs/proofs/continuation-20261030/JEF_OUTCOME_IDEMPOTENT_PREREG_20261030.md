# JEF WP-U1 self-outcome FINAL retry idempotency — preregistration 2026-10-30

Parent PR #1177 verified head `c55b8e6f54ce28a7ec7e2400809f051e0ec94b81`; child review-only. Own `v13/code/v13/jefoutcome.py`, new `tests/test_jefoutcome_idempotent_20261030.py`, focused CI, raw and build-state delta. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Failure hypothesis
`after_turn` accepts a FINAL event more than once, appends a new self-label for the same (event_id,component), creates a new source row and increments `JEF_OUTCOME_LABELS` version. Its `report` counts duplicated outcomes, and after a route correction flipped `skill→none`, replaying the original FINAL can append `skill` again. This is a retry/restart integrity defect in learning evidence, not model quality.

## RED-first controls
- Real Runtime/Store; register `ExecutiveDecision` for a skill event and call `after_turn(... FINAL ...)` twice. The second receipt must be a true no-op: one retained label, identical state+version, no extra `OUTCOME_SELF_LABEL` source row, stable report.
- Apply route correction `skill→none` once and repeat the original `after_turn`. It must not resurrect `skill`, duplicate label or allocate a source; return the persisted `none` target.
- Repeat after real SQLite close/reopen.
- Two different events with identical text/context must each retain their own label, not be deduped globally.
- `ERROR` or missing decision produces no labels. Existing JEF/SkillLive/Context OS tests remain GREEN.

## Repair
Create candidate rows without source writes. Use optimistic state-version CAS to add only **missing** (event_id,component) labels, preserving the first finalized label and later explicit correction. On an unchanged retry return the persisted value without a state write or new source. Bound by existing MAX; do not change learning modes, approval, weights or other organs. Concurrent CAS collision may leave unused source blobs from a failed attempt; do not claim cross-process exactly-once source allocation without a transactional source API.

## Evidence
Prereg first, test-only original RED, then source fix and exact-source GREEN with complete raw, source/Canon hashes, SHA256SUMS, CRC, privacy/diff. Full unfiltered parent #1174 retains historical frozen Run34/Run37 errors; no native/Redmi or STEP2/B3/JEPA/whole-system gate promotion.
