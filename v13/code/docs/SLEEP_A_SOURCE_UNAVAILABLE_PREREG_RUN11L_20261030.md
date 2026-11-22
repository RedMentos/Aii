# Sleep A replay source-unavailable fail-closed handling — prereg 2026-10-30

Owner GPT-6, review-only child of #1240 exact `645c70e8c28fb9e016eaa5d068c2d3977075184d`. Independent file ownership `v13/code/v13/sleep.py`, new synthetic real-Store tests, CI and scoped docs only. The full unfiltered run11k on the exact parent is independent/in progress; do not claim its result here.

## Defect hypothesis
`SleepCycle._probe` currently treats any `ValueError` while reading an event source as `RETIRE/SOURCE_DELETED`, conflating a deliberately revoked source with a corrupted/mismatched live source. A missing live blob raises `OSError` and escapes `_probe`, potentially aborting Sleep A and skipping unrelated healthy replay. Silent retirement destroys the schedule's chance to retry after repair. This is a real source-retention and replay-continuity problem, not an optimizer/model/JEPA proof.

## Test-first frozen cases (no native)
Use a temporary actual Store, Memory and SleepCycle; create a user event and explicit `fact` correction (a real replay row). Before patch assert:
1. Healthy exact source + verified correction remains `PASS`.
2. Explicitly tombstoned original event source remains `RETIRE/SOURCE_DELETED`.
3. Live event source whose backing blob file is missing returns `FAIL` with `EVENT_SOURCE_UNAVAILABLE`, `source_integrity` affected path and original source ref, not an exception or retirement.
4. Live event source whose blob bytes are corrupted (hash mismatch) returns the same `FAIL`, not `RETIRE`.
5. A Sleep A batch with one unavailable and one healthy source completes, counts both outcomes, retains failed evidence and does not write any facts/weights.

## Patch contract
Read-only source-row tombstone check distinguishes explicit deletion from unavailable/corrupt live bytes. Catch `ValueError/OSError/UnicodeError` for a still-live source and emit a typed FAIL with original SourceRef, check and affected path. A malformed event envelope should similarly fail closed, not turn into authority. Keep tombstone RETIRE behavior, unchanged queue policy, sleep authority, Age0, raw failed attempts and every negative gate. No automatic recovery, file recreation, or source substitution.

## Proof
Preregister first, test-only original RED in isolated GitHub Actions, minimal patch, focused GREEN plus existing Sleep A/validation/memory authority tests, compile/privacy/diff, original ZIP SHA256SUMS, private backup and byte readback. No native/Redmi. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; whole V13 INCOMPLETE.
