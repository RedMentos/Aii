# C5 feedback-ledger persisted-input integrity — review-only (2026-11-08)

Owner: isolated C5 review branch `codex/c5-ledger-integrity-20261108`. Parent: `codex/c5-event-ledger-candidate-20261108` / PR #1606. Source: `v13/code/v13/c5_feedback_ledger_candidate.py`.

## Finding
The candidate v1 used `context + '|' + action_id` as an aggregate key while allowing `|` in both fields. Distinct bindings such as (`a|b`, `c`) and (`a`, `b|c`) therefore alias and mix human credit. Its `record` path validated only the new event, not all persisted rows; `aggregate` accepted ambiguous persisted binding values and extra row fields. This is a correctness/provenance issue, not evidence of learning utility.

## Candidate change
Reject the reserved delimiter in both binding fields; validate the entire persisted ledger (revision, exact row shape, ID bounds, score bounds, max capacity) before record or aggregation. This is intentionally fail-closed, without migration or C5 runtime activation. Historical rows containing a delimiter need an explicit versioned migration rather than silent reinterpretation. This is compatible with ordinary existing keys without delimiters.

## Verification status
GitHub readback confirmed source blob `0dc9359f1a1359ede5ab08363dad87583925ba4e` and new adversarial test blob `45b32590d18861a9c9e06b06da50ea7325b57297`. Exact checkout tests **NOT RUN**: direct container Git access failed with `Could not resolve host: github.com`. The new test cases are unexecuted; no PASS is claimed. Required command on an exact checkout: `cd v13/code && python -m unittest tests.test_c5_feedback_ledger_candidate tests.test_c5_feedback_ledger_integrity -v` (or discovery if tests is not a package). Then run broader C5/Neuromod consumer tests, independent review and privacy scan.

## Open acceptance and next work
No runtime consumer; no CAS/transactional Store binding; no restart recovery proof with actual Store; no historical EMA reconstruction/migration; no C5 credit authority. Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/JEPA negative gates, Age-0 SHADOW. Next: run exact-source tests, inspect current Store API and implement a separate source-bound CAS adapter with deterministic retries, then test restart and duplicate/correction under concurrent writers. Do not merge or enable until independent review and original gates pass.
