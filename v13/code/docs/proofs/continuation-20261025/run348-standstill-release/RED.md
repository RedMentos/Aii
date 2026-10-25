# Run348 observed RED (2026-10-25)

- Frozen prereg commit: `e37aa4a869142594d6fb3b9bce547699ec0d61ca`; RED exact-head commit: `667735caa1d9fb3ed8c4593ac6ae451cf6c69c78`.
- GitHub Actions: run `40224037393`, job `121261520796`, **FAILURE**, 18 real Runtime/SQLite tests: original 14/14 PASS, new 4/4 RED (2 failures + 2 errors). Source is unchanged in this phase. `tests.test_standstill` baseline PASS.
- Observed failures: failed STANDSTILL CAS already relaxed protective guards; interrupted release lacked a durable `release_pending` marker, so retry/restart/re-engage semantics could not be proven.
- Downloaded raw ZIP artifact `12610546995`: SHA256 `7650ec671bca86f0fce6bbe66c9f4cb27a74291424fb7b0234503758686c6004`, CRC PASS, internal SHA256 manifest **3/3 verified**, embedded `RUN348_HEAD.txt` matches exact head. Privacy scan not reached because RED test step stopped the workflow (do not claim privacy PASS at RED).
- Private durable backup verified as uploaded: `/V13/checkpoints/2026-10-25/V13_Run348_Standstill_Release_RED_raw_sha7650ec67.zip`.
- Next: smallest two-phase release implementation, GREEN exact-head CI and independent raw ZIP audit. No native/Redmi/STEP2/B3/Body-JEPA/AG6/V13 promotion.
