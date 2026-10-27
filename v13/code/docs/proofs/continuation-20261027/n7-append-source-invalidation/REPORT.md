# WP-N7 append-only source invalidation — 2026-10-27

**Review-only child of PR #720** (exact base `acaaefde09072e38cb541f82fb2182bb8b9d11de`), not integrated into old `main`. Owner: `codex/automation11-n7-append-source-invalidation-20261027`.

## Defect and negative controls

The append-only cache re-entry previously accepted the last event ID and stable system text without checking that the previous volatile layers or older source-valid history were still the same. After a memory was removed from the active view, a stale `prev['messages']` could still carry its content into the next planned prompt. A rewritten earlier source turn could likewise be replayed. Switching from SHADOW to ACTIVE could re-enter a counterfactual prompt that had never actually been sent to the model.

Added RED counterexamples for revoked volatile memory and rewritten earlier history. The patch binds each retained transcript to the exact volatile serialization, prior source-history turns, last user query, and whether the plan was actually applied. Any changed source, missing legacy fingerprint, or SHADOW-to-ACTIVE transition falls back to rebuilding the prompt; no source is silently promoted. An unchanged source-valid prefix in ACTIVE retains append-only re-entry. New tests also cover rewritten last user text, SHADOW-to-ACTIVE, and ACTIVE-to-ACTIVE positive re-entry. The existing SHADOW counterfactual positive test now keeps volatile source unchanged.

## Evidence / pending verification

- Test-only RED commit: `9a9551c4456f8a837a9220c17831f01332000b46`, Actions `40517444470` (result pending at checkpoint).
- Fix commit: `d64f171008968686aafd03613b851f30e769ca58`.
- Expanded tests commit: `a3dee8063794a9ba79781eddd5598b602ff7c305`, Actions `40517582552` (result pending at checkpoint).
- Focused command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_context_os`.
- CI workflow `.github/workflows/n7-append-source-invalidation.yml` runs the focused tests, compile, privacy scan, and diff check without model downloads.
- **Do not claim PASS until exact-head Actions evidence is inspected.** RED, failures, and skips must be retained as observed.

## Limits / continuation

This is a software/source-view integrity candidate, not a native cache-performance measurement. It does not establish revoked-source invalidation in any other subsystem. `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `BJ1=NO_SIGNAL`, registered `jepa_weight=0`, Age authority 0, Redmi unmeasured, full V13 incomplete.

**Next command:** inspect exact-head Actions and the original RED job, then independently review the cache re-entry diff; run the broad software suite on the candidate before integration. Continue other canonical work while Actions are queued. Do not merge into `main` directly.
