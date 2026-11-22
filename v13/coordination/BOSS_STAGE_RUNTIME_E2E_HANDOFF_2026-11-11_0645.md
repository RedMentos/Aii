# Boss integration handoff — 2026-11-11 06:45 Europe/Berlin

## Verified scope
Parent: #1738, branch `boss/v13-integrated-stage-20261111-0545`; this PR changes only one Boss-owned test. Current parallel QA #1740 already tests **real pin staging and compile**, but NOT a Runtime turn. Research #1739 and JEPA #1737 are separate; neither is silently merged. Root/v13 AGENTS, Canon v10.16.1, ROADMAP, BUILD_STATE and the current integration handoff remain binding. No runtime/model/GGUF changes.

## New executable integration proof (pending execution)
`tests/test_pinned_stage_runtime_e2e_20261111.py` stages the actual hash-pinned multi-organ builder (not a mocked builder), then launches the **materialized Runtime** in an isolated Python subprocess. It reuses two existing concrete synthetic tests:
- `test_real_operator_turn_update_restart_and_revocation`: SQLite event, RECORD_ONLY refusal, explicit SHADOW+HUMAN bounded World update, checkpoint, restart, no duplicate update, source revocation refusal.
- `test_archived_user_source_remains_verified_for_world_then_revocation_quarantines`: submitted Runtime turn, blob archiving, Unicode span read, World prediction, restart, revoked source cleanup and fail-closed World/archive read.

C3 native weights are replaced by the established deterministic `synthetic_c3` test driver. No native quality, actual human-labelled utility, full JEPA/EMA, real Perception→Body→C3 path, Redmi measurements, or production learning authority is claimed. This closes a test coverage gap **only if it passes on exact integrated source**.

## Run
```bash
cd v13/code
python -m unittest -v tests.test_stage_integrated_candidate tests.test_pinned_stage_runtime_e2e_20261111
```
Requires pytest, numpy and the existing integration dependencies. An actual GitHub checkout cannot be obtained in this execution environment (github.com DNS fails), so exact-head test execution is **UNVERIFIED**. Do not mark PASS until CI or a verified checkout executes it. A failing test is a release blocker to diagnose, not an excuse to weaken source/learning gates.

## Next delivery tasks
Boss: get this executable test green on exact pinned branch, then integrate approved #1739 PerceptPacket and #1737 T8→WorldJEPA paths in a single candidate; test one real end-to-end turn and holdout/restart. Core: connect ordinary Runtime C3 output to source-bounded ContextOS retrieval, no arbitrary tools. JEPA: provide measurable disjoint holdout utility from actual trusted transitions. QA: reproduce/fix the first red integrated test, run memory/low-RAM checks. Perception: pass source-bound PerceptPacket into ordinary B1/B2 Runtime. Keep separate ownership and review, no automatic merges.

No release promotion. Stage=SHADOW/REVIEW_ONLY. Canon completion=false.
