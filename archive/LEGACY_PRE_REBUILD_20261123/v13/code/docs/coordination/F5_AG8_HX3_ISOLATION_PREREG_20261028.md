# Cross-organ F5 / AG8 / HX3 / ContextOS / Sleep A authority isolation — preregistration, 2026-10-28

Parent review-only PR #806 head `5aa5888e32c158aab67ed5d8d1b9f6b19c1b70eb` (parent CI pending at registration). Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` must remain unchanged. No changes to registered model/seed/source cohorts or production main.

## Question

After a real Runtime/SQLite restart, can an F5 HumanDecision deletion and an independent AG8 request revocation each invalidate only its own read-side authority, without destroying unrelated ContextOS warm facts, Sleep A recall probes or HX3 ExperienceLibrary lessons? This integrates the separately tested guards from PR #803/#804 rather than treating separate passes as proof of composition.

## Test preregistration (before any test or source edit)

Create two source-backed F5 human fact memories and two independent approved AG8 harness proposals with evidence-backed HX3 lessons. Verify both ContextOS warm facts, both Sleep A probes and both HX3 lookup rows before restart. After restart:
1. Revoke only the first F5 HumanDecision source; assert first warm memory excluded, first Sleep A probe not PASS, second warm memory/probe still PASS; HX3 both lessons remain valid.
2. Revoke only the first AG8 approval request; assert first HX3 lesson excluded without explicit verify, second lesson still returned as DATA_NOT_INSTRUCTION; unaffected second ContextOS warm fact/Sleep A probe still PASS.
3. Assert zero `updates` and no changes to Age/learning policy. Use deterministic synthetic F5/AG8 evidence; no native inference, training, Redmi or live HX consumer.

Test should be runnable under `PYTHONPATH=.:tests python -m unittest -v tests.test_f5_ag8_hx3_authority_isolation_20261028`. Preserve focused and full Linux software raw exits, SHA256 hashes, source Git blobs, privacy scan. If a test fails, fix only the proven gap on a new review branch or within this branch with a RED/GREEN record; do not call partial success acceptance. Original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0, V13 incomplete. Owner: GPT-6 independent cross-organ integration test package.
