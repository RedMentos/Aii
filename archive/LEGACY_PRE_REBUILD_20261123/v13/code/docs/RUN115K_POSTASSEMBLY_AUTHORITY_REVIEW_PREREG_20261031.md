# Run115K-R independent post-assembly authority review — preregistration (2026-10-31)

Owner: independent GPT-6 review; base exact Run115K implementation commit `5edf9d64e2c0793a942e99f0af2f9c049d477a5b`. Separate review branch, no changes to Run115K owner branch, Canon, registered native cohorts, model/seed hashes, or production Runtime.

## Hypotheses registered before tests or fixes

1. A typed JEF formatter result may claim candidate A/10 while its *user-role JSON* embeds B/30 or authority=1. Run115K bridge currently checks `sources` only and may return VERIFIED with contradictory typed payload. This is an integrity/authority boundary, not a model-performance question.
2. A final post-assembly JEF `propose` may preserve candidate and source hashes but change `status`, `authority`, `native_calls`, `model_called`, `store_writes` or `tool_dispatches`. The bridge's existing postcheck compares only reason/candidate/hashes. It must fail closed if the final result is no longer the same zero-authority recipe.

## Fixed verification

- New isolated adversarial `tests/test_run115k_postassembly_authority_review.py` uses explicit synthetic collaborators to exercise the exact bridge function and inject contradictions after otherwise valid source/offer/typed assembly. Positive control must retain SHADOW verified prompt and user/system separation; each tampered control must refuse with no messages and no authority.
- Existing real SQLite/Context OS B1/B2 envelope and typed JEF tests remain required; synthetic mocks do NOT establish native B1/B2, C2, JEF, C3, quote correctness, or STEP2 utility.
- Run focused Python unittest and `compileall` in CI; verify GitHub Actions result and source commit; preserve original negative gates. New branch is review-only, no production integration or merge.

Age0 RECORD_ONLY; STEP2 EXIT EVIDENCE_NOT_PASSING; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; `jepa_weight=0`; Redmi unmeasured; whole V13 incomplete.
