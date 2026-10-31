# Auto11 — Run84 dual-source JEF/B1/B2/C3 -> C5/F3 DRAFT -> C6 read-only preflight (2026-10-31)

Owner: GPT-6 automation; isolated review branch `assistant/v13-auto11-dual-source-c5c6-draft-20261031-1205`, exact parent Run84 PR #1444 `7f5875e46036dd1278303dd74461a7bb6dfc24da`. Independent of Run85 native owner, Run87 seed877 owner and original native cohorts.

## Question / bounded software claim
Can the already source-authenticated, default-OFF Run84 JEF/B1/B2 C3 JSON formatter result be passed ONCE to the existing source-only, transactional JEF/C5/F3 DRAFT stager and C6 read-only preflight, with no second model call, no TTY approval, no delivery, no tool dispatch, no learning, and no B1/B2 hypothesis promoted to truth?

Acceptance: real SQLite synthetic test covers exact JSON A/B/NONE, opt-in gates, malformed/duplicate/wrong formatter, stale/revoked sources, idempotent duplicate DRAFT, post-guard and post-stage source mutation, C5/F3 tamper, and orphan-DRAFT reporting when a race occurs. The stage must reuse the already validated C3 result; it MUST NOT silently call a model again. Check full dual-source prompt hash before/after staging and C6 preflight; preserve all original source-bound JEF transaction checks. Preserve exact current-source references; no persistent dual/C3 receipt claimed unless explicitly implemented. A successful result is SHADOW only and not a production-delivery credential.

## Implementation/test
Add only isolated `v13/code/v13/jef_b1b2_c3_c5c6_draft_shadow.py`, `v13/code/tests/test_auto11_dual_source_c5c6_draft.py`, isolated CI workflow and checkpoint. Do not edit Canon, runtime, Run84/82/75/77/83/87 files or existing preregistrations. Use existing Run84 `evaluate`, existing `jef_c3_c5_c6_fallback_draft_candidate.stage/preflight`; bind returned SHA values and recheck source after transaction. No native calls in tests, no false native evidence.

## Known limits
The existing stager persists a JEF prompt hash, not the combined B1/B2 dual-source prompt hash or native C3 output receipt. A race after C5 staging may leave an orphan SHADOW DRAFT; report it explicitly, never claim rollback. The callback is trusted, not sandboxed. No native model proof, real output, approval or semantic utility. Historical full-suite RED 4 FAIL/66 ERROR/28 SKIP; Run70 source-only C3 RED; Run77 B1/B2 RED; Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole-system incomplete.

## Verification
Run `PYTHONPATH=v13/code:v13/code/scripts python -m unittest -v tests.test_auto11_dual_source_c5c6_draft tests.test_run84_dual_source_c3_postgen tests.test_jef_c3_schema_source_recheck_shadow`, compileall, privacy scan vs exact parent and git diff --check. CI original raw with stage exits and hashes, report software only. No heavy owner contention.
