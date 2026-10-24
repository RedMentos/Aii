# Run86 verified result — Linux extracted phone ZIP operator journey

**Exact source head before evidence:** `edd0dc29a92747e4dfe58db9b586315f086e67b6` (PR #119); base Run85 `0947d51e9fe34bb441f672f6f11a388f5e823224`. GitHub Actions run `40134506421`, job `120993056078`, 2026-10-24 UTC, **SUCCESS**. GitHub Actions ran a synthetic PR merge commit `9e878496efe623e6fab039b6348ad75c31edc12a`, not the branch-head commit; this distinction matters for source ZIP provenance.

- Existing full-checkout focused Linux suites: **377/377 PASS** (11.649s). Not the entire repository suite.
- Official added-lines privacy scan `0947d51e9..HEAD`: **CLEAN**.
- Phone ZIP: **809 source files + manifest**, 12,540,865 bytes, archive SHA-256 `e5a7bbf047d0f910cf3f9b5fecf05feb29a54ded2e81ab399d960667fa099bd2`; independent verifier matched.
- Extracted source ZIP: **74/74 software tests PASS** (16.679s), including three new Run86 tests (FIFO exact-copy/source binding/export across restarts, standstill persistent gate and release, local operator origin/default RECORD_ONLY). `EXTRACTED_PHONE_RUNTIME_RESTART_PASS`.
- GitHub Actions artifact `V13-Phone-source-9e878496efe623e6fab039b6348ad75c31edc12a`, artifact ID `12576242377`; uploaded artifact wrapper digest `aad05a27f41226eecb32c3f94cd6ac77304bceb776769b16ec40d39c065a8c05` is **not** the inner phone ZIP digest. Artifact is time-limited by workflow retention 30 days. Durable source is on the review branch.
- Raw evidence: `CI_RUN86_RAW_EXCERPT.log` and full GitHub Actions job log (run above). No failed tests were observed in this run. No model download, native inference/training, Redmi measurements, semantic second-attempt utility, or full suite.
- Gates unchanged: STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; `canonical_architecture_complete=false`; `user_full_scope_complete=false`.

**Owner:** Run86 tests, one workflow invocation, Run86 proof only. **Next:** independently review PR #119, preserve this exact ZIP/artifact provenance, then address one-shot `python -m v13 ask` operator-rule ingress parity as a separate package. Do not silently claim that this ZIP is a native phone install or end-to-end learned system.
