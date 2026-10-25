# Run133 — independent security review of Claude HX1/HX3 shadow proposal authority and evidence freshness

2026-10-25 UTC. Base exact Claude source imported in Run132 at `8be4354e195c3c13a44686a1f878592a3a22b6a2`. Original Claude blobs and 64/64 GREEN preserved in Run132 PR #162. Run133 owns ONLY `v13/agi/harness.py`, `v13/agi/experience.py`, new tests/workflow/proofs. No Runtime, self_improve, hub, models, Canon, hard prompts or live activation edits.

Cross-review finds:
1. `HarnessLibrary.apply` trusts a caller-supplied dict with `status='APPROVED'` and `shield.passed=True` but does not bind to persisted AG8 proposal and approved request.
2. `ExperienceLibrary.record` has the same forged-approval acceptance; evidence file existence alone is not human approval.
3. `ExperienceLibrary.lookup` can serve an ACTIVE note whose evidence bytes changed after record until an explicit `verify()` call.

Test-first RED: forged dict must be refused by both APIs, legitimate AG8 approval must work, changed evidence must be excluded automatically at lookup without explicit verify, stale report must be marked. Hardening must fail closed and preserve original Claude 10 tests. Avoid expensive writes on every unchanged lookup if possible; no live consumer exists. No new external authority. No model/native/Redmi/utility or AGI claim. All original negative gates unchanged.