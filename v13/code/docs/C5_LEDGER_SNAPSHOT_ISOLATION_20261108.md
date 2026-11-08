# C5 ledger snapshot isolation — review-only (2026-11-08)

Owner: `codex/c5-ledger-snapshot-isolation-20261108`. Parent: PR #1607, head `f257924110ec24097f4d229bca1febd5eb6a7856`.

## Finding and patch
`record` used `dict(old)`, which copied only the event map. Previously stored row dictionaries were shared between the input and returned states. A caller mutating either state could silently change effective credit in the other snapshot, undermining correction/restart/CAS assumptions. This is an in-memory aliasing defect, not evidence of active learning. Replace the shallow map copy with a per-row dictionary snapshot, preserving the existing v1 JSON shape, bindings, capacity and all negative gates.

## Evidence and limitations
Added `test_record_returns_independent_nested_snapshot` covering mutation in both directions and a subsequent correction. Exact repository checkout tests **NOT RUN**: `git ls-remote https://github.com/RedMentos/Aii.git HEAD` returned `Could not resolve host: github.com` in the execution container. No native/model test, privacy scan, CAS consumer, migration, or production integration was performed. GitHub connector source readback is required before review; test is committed but unexecuted.

## Next command and acceptance
`cd v13/code && python -m unittest discover -s tests -p 'test_c5_feedback_ledger*.py' -v`, then focused C5/Neuromod consumers, independent review, privacy scanner and an actual transactional Store adapter. Explicitly test duplicate delivery, correction, restart, and conflicting writers against the real Store. Do not grant feedback-learning authority or reconstruct historical EMA without separately verified migration. Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/JEPA and Age-0 SHADOW. No changes to weights/cohorts/source pins.
