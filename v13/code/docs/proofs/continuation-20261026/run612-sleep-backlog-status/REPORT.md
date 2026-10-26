# Run612 — read-only Sleep A digest backlog status, verified

Recorded 2026-10-26 UTC. Review-only PR607, child of Run611 PR606 verified head `b292302dff5b3c425e97010bc5460e4cf83eaac2`. Owner GPT automation11.

## Functional result

The persistent Termux operator now accepts `:sleep digest status`. It reads **only the active session** and returns digest cursor/version, retained entries, deferred assistant-ID count, unscanned assistant rows and FINAL assistant rows, legacy v1 backfill indicator, `has_work`, 64-turn cycle cap and fact_authority=0. No chat text is returned; unscanned counts are explicitly `NOT_EVALUATED` for source validity. Read-only status neither migrates v1 nor triggers a sleep, changes Age/learning/approval rights, or writes any state. Existing `:sleep digest`, `:sleep run a` and scheduling remain unchanged.

Prereg before edits `dfc3c3b8aebba18374f23e3ba9fdd6fcc2f9d553`, SQLite/Runtime test commit `ba4dee3afd66195b0c4a94e974b27879cbebe531`, source commits `2e8e8acfb3e2a346b84d041dbc2f2ab7d5e7fce5`, `b7d848e84c69b4cf7a43148925f95f2ce05120af`, `ef44de985ea4f4c037c5ab9b8aa3a49e8f18fe0a`, CI workflow commit `e2d95b0a78f9d7937155d9540ec7b2745e5d5931`.

## Closed evidence

- Actions `40406022308` at exact code/workflow head `e2d95b0a78f9d7937155d9540ec7b2745e5d5931`: **SUCCESS**, actual Linux SQLite/Runtime **78 executed tests OK (111.771s)**, privacy CLEAN. **Note:** Run610 and Run612 test modules import Run609 TestCase class directly; unittest discovers it again in each module, so the 78 executed cases include 12 duplicate Run609 cases (66 distinct test methods). This is a test-collection efficiency issue, not additional independent coverage. Do not claim 78 independent cases.
- Original raw artifact `12690293505`, ZIP SHA256 `7c6009ebff341b0a1e5e5833745a8514a2a597bcd7c2b3b82b0a66fd26e5fcd7` matches GitHub artifact digest; all **7/7** manifest entries independently rehashed. Test/Privacy exit 0. Source SHA256 `sleep_offline.py=688057fd0165f812d9bac40913530872aad6b861e6857d292f35c9dff93a08b7`, `sleep.py=331ddd62cede7d3c4f2b46151d32d08925c1fd40f6ef33b4c98af960a3708a7e`, `operator.py=842f7933a542f4842fea17e1489d39f462cb4ed005de723019f0893aa77105f7`.
- This is source-only; no native model, Redmi performance, or broad unfiltered full-suite proof. Parent PRs are review-only, not main.

## Negative gates / next

STEP2=UTILITY_FAIL; B3_L1=FAIL; Body_JEPA=UNAVAILABLE; jepa_weight=0; Redmi=UNMEASURED; V13=INCOMPLETE; canonical and user full scope false. Original Run596 unfiltered suite RED preserved. Open: independent review, actual Redmi long-session observation, >128 deferred fail-closed limit, native Body-JEPA/sparse train/receiver and semantic STEP2 utility.

Exact source-only reproduction from repo root:
`cd v13/code && PYTHONPATH="$PWD" python -m unittest -v tests.test_run612_sleep_backlog_status tests.test_run610_sleep_partial_pair tests.test_run609_sleep_digest_backlog tests.test_sleep_offline tests.test_history_lineage tests.test_context_os tests.test_sleep_scheduler tests.test_sleep_validation`

Next owner unassigned; next priority a **different** canonical functional/learning package, not further isolated Sleep helper hardening. No authority promotion.
