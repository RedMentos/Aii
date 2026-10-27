# G13 scheduler in-flight capacity: independent RED/GREEN review

**2026-10-27 UTC; owner:** GPT-6 continuation; review-only child of PR #737 exact `3b6ce3fb75f99fb8b44ad555e34f30a29c9307e3`. Parent's scheduler blob `16bc01f68c3e2e9456881262866c384ed9441809`; canonical SSOT untouched.

## Confirmed defect

The scheduler advertised `MAX_PENDING=256` but `_post` counted only `PENDING/HELD_AGE` records. `DISPATCHED` events remained in the same persisted `events` array and could accumulate without bound if jobs stayed in flight. A second test showed a pending low-priority event was not evicted when two in-flight jobs occupied the other slots. This is a queue-capacity integrity defect, not a demonstrated exploit of Age/learning authority.

## Exact-source evidence

Preregistration committed at `32febc7abab7d3c6b4f7ccdac3a41e44700b8b0f` before tests/patch. RED test-only commit `9bb514de1c666f5cf992bd1813678b29c1ca6588`, Actions `40532009512` **expected FAIL**: 10 tests, 2 capacity counterexamples FAIL, 8 PASS; INSTALL/COMPILE/PRIVACY/DIFF exits 0, UNIT exit 1. Original raw artifact `12744999500`, ZIP SHA256 `fb70c59d184a8f4e140bbe09163d5cb9da844fbd69e3fb66c32468b1b77147ab`. Raw ZIP CRC, HEAD, exact failures and exits verified; privately backed up byte-identically at `/V13-Checkpoints/2026-10-27/Automation11G-Scheduler-InFlight/RED-40532009512.zip`.

GREEN source commit `099c6bad7ecfb7672ed5844182ab7f01e930b660`, scheduler blob `e1704de76e77947849c5b0a9b2f174ce47f1a29e`. The capacity guard now counts `DISPATCHED` alongside `PENDING/HELD_AGE`; only lower-priority pending/held background victims may be evicted, never in-flight jobs. Focused Actions `40532090041` **10/10 PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits all 0, raw artifact `12747146178`, ZIP SHA256 `5fd2a0e45c7139ac5ae7650e9b4397ae46bbd9f9d5059deedb5c73fb84b1d895`. CRC/HEAD/source blob/exit evidence independently checked; privately backed up byte-identically at `/V13-Checkpoints/2026-10-27/Automation11G-Scheduler-InFlight/GREEN-40532090041.zip`.

Full software suite at exact source/workflow head `6c1085039daf5aec7bb24c799984e3264dc8a804`, Actions `40532176820`: **1904 tests OK (1 skipped)** in 145.878 s, INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits all 0. Raw artifact `12746777353`, ZIP SHA256 `04760be4a601a8fe9170c80b796f347fe890a5c96842fa301a3c32ce537f510e`; CRC, exact HEAD, scheduler blob and exits verified; private Library backup re-downloaded byte-identical at `/V13-Checkpoints/2026-10-27/Automation11G-Scheduler-InFlight/FULL-40532176820.zip`. This is software-only evidence, not a native or Redmi measurement. Original PR #737 full suite `40529741869` completed successfully at `c98d3ca8e63fb8d2dc0b9f74d635c0218909db25`; that result is inherited context, not evidence for this changed head.

## Gates / next

LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured, V13 incomplete. No native/model work or production/main merge. **Next:** independently review the exact full-suite-passing diff, then examine separate foreground-kind action spoofing boundary (SYSTEM `TOOL_EVENT` with background action currently bypasses idle/resource/budget in `_allowed`). Preregister before altering that boundary; verify legitimate RESOURCE_CHANGE event path and all existing priority tests. Continue other blueprint packages in parallel without overwriting their owners.
