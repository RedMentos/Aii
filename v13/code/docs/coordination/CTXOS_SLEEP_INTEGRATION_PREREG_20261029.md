# Context OS × Sleep S7 exact-source cross-organ integration prereg — 2026-10-29

## Frozen before integration
- Base: PR #1110 branch `codex/v13-sleep-digest-backlog-review-20261029-auto10`, commit `8fe501dbf38d25e66d3141ff771d9c36fa25c448`, child of PR #1104.
- Independent donor: PR #1109 branch `codex/v13-contextos-source-restore-review-20261029-auto10`, commit `e93f49455b1db4b7dd606582d155e5e4fc85e06b`, also child of PR #1104.
- Import donor files byte-identically: `v13/code/v13/context_os.py`, `v13/code/tests/test_contextos_source_restore_20261029.py`, donor handoff/prereg and donor workflows. No edits to frozen model, source cohorts, seed, Canon or Age policy.
- Retain PR #1110 `history.py`, `sleep_offline.py` and original raw evidence unchanged.
- New independent test ownership: `v13/code/tests/test_contextos_sleep_source_integration_20261029.py`. New workflow/handoff only; do not mutate donor-owned source.
- Test matrix: exact Unicode/numeric/source text after >64-turn digest backlog; explicit read-only retrieval during partial catch-up; tombstoned current-session source denial after catch-up; unrelated-session denial; S7 source-valid history and digest high-water unaffected by source retrieval.
- Negative claims: no model calls, no learned quality/weight update, no Redmi measurement, no B3 latent authority; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Age0 RECORD_ONLY, V13 incomplete.
- Evidence protocol: dedicated exact-head GitHub Actions focused and full software tests, compileall, privacy scan, diff check; raw logs with SHA256SUMS uploaded even on failure; record original RED/FAIL and preserve artifacts. Independent review required before merge.
