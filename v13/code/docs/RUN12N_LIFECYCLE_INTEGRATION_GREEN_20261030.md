# Run12N isolated real-lifecycle software integration (2026-10-30)

Review-only child of Run12N native utility PR #1273. New `tests/test_c2_body_observer_off_lifecycle_integration.py` exercises the actual candidate `fresh_turn` code path through real `initialize`, fresh per-turn home/config, `Runtime(home)` signature (mocked native execution only), `submit` event ID, `audit_event` Store contract, preclose persistence, `close`, postclose runner-release receipt, observer-OFF and negative gates. Explicit missing-release counterexample fails closed. No native models, no model-generated utility and no production route change.

Exact-head GitHub Actions `41061598155` SUCCESS at `26dcee3bd3e7a6c0bcaefdef5312ae141c885c4d`: **45/45** source-only tests PASS, 8/8 stage exits 0, privacy CLEAN, source pins matched. Original ZIP artifact `12978539268` SHA256 `26a5bf12fc53906bf943166017dd92b73e55cdf4673f80041a6216304bc5b1de`, CRC clean, 18/18 inner SHA256SUMS matched. Private Library copy: `/V13-Checkpoints/2026-10-30/Run12N-ObserverOff/LIFECYCLE_GREEN_41061598155_sha26A5BF.zip`; byte-exact readback pending.

Independently verified real Linux-native Run12N `41061289187` remains **16/16 structural GREEN, utility RED** (C3 0/8, B1 3/8, B2 4/8, C2 auto 1/8). This test-only package does not re-score or modify that result.

Next: read-only full-task diagnostic for original source-bound remainders + faster-option claims; preregister a new disjoint no-model baseline and C2 utility comparison before any routing policy change. Gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole system incomplete.
