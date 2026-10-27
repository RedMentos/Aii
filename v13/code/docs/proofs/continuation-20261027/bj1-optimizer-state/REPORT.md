# BJ1 optimizer-state exact-resume integrity — 2026-10-27

**Review-only child of PR #719** (exact base `cf136b516f55b70212dbd5aeebe0441f6426d819`), not `main`. Owner: `codex/automation11-bj1-optimizer-state-integrity-20261027`. The original BP2b seed41 native timeout and all negative gates remain unchanged.

## Defect and fix

The checkpoint verifier accepted a payload with an empty AdamW `optimizer['state']` after a completed step, as long as the hash and source pointer matched. `optimizer.load_state_dict` would then silently restart with empty moments, violating exact continuation. It also accepted a partial nonempty state slot missing `exp_avg` or `exp_avg_sq`.

The candidate refuses a completed-step save with no optimizer state and rejects missing optimizer state, incomplete per-parameter AdamW slots, invalid/nonfinite/out-of-range step counters, and mismatched moment shape/dtype **before** mutating the live adapter/predictor. An unused predictor in a CE-only arm may legitimately have no state slot; that remains allowed. Existing optimizer parameter-name/order and source/config/EMA/RNG guards are retained.

Synthetic negative controls deliberately reserialize and rehash incomplete checkpoint blobs and update their pointer, so rejection cannot be attributed only to the outer SHA guard. Tests also assert adapter parameters remain unchanged on rejection. The positive exact uninterrupted-vs-resumed trajectory remains part of the focused suite.

## Evidence and gate limits

- Test-only RED commit `53f9c3b0f3dbe53fde3eaaa43c43ea5b53cde0d0`, Actions `40517824916` (pending at checkpoint).
- Fix commit `098102621eefbfd382111345534baae693aa7697`; expanded tests commit `63ac50f1bc8b8246fcb115085ab98ce18525c51f`, Actions `40517894874` (pending at checkpoint).
- Workflow `.github/workflows/bj1-optimizer-state-review.yml`: pinned CPU Torch, `tests.test_body_jepa_checkpoint`, compile, privacy scan, diff check; no model download.
- **Do not claim PASS until exact-head Actions logs are inspected.** Preserve original RED and any failed attempts.
- This is a synthetic software-only integrity candidate. It is **not** a native LFM2 body run, Redmi evidence, JEPA utility proof, or age promotion. `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `BJ1=NO_SIGNAL`, registered `jepa_weight=0`, Age authority 0, V13 incomplete.

## Verified focused helper result

- Actions `40517894874`, exact source `63ac50f1bc8b8246fcb115085ab98ce18525c51f`: **11/11 synthetic helper tests PASS**, Python compile PASS, privacy CLEAN, diff check PASS. The log confirms the rehashed missing-state and missing-slot tests, plus no-state save refusal.
- Original test-only RED run `40517824916` was **CANCELLED**, not a measured failure. A separate immutable RED witness branch `codex/automation11-bj1-optimizer-red-witness-20261027` at `e4a7fefb6b4a542376c54fef479ff20233b1a2c1`, Actions `40518210679`, is pending. Do not invent its result.
- Tiny synthetic HF/PEFT exact fit-resume Actions `40518115903` is pending. The helper result does not replace integration/native evidence.

## Closed RED witness and tiny fit result

- Independent RED witness Actions `40518210679`, exact `e4a7fefb6b4a542376c54fef479ff20233b1a2c1`: **9 tests, 1 expected FAIL**, `ValueError not raised` for a rehashed missing Adam optimizer state. This does not turn the cancelled original RED job into a completed run.
- Tiny HF/PEFT synthetic integration Actions `40518115903`, exact `a506cb9d80d9a50f593a55ab9ed9e9f3830ae850`: **12/12 PASS**, including interrupted `BodyJepaTrainer.fit` == uninterrupted, compile PASS, privacy CLEAN, diff check PASS. No model downloaded and no native LFM2 utility claim.
- Separate integrated N7+BJ1 review branch `codex/automation11-bj1-n7-integration-20261027` has its own pending full-suite gate; this candidate's 12/12 is not a whole-system PASS.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_body_jepa_checkpoint tests.test_body_jepa_checkpoint_fit` (requires CPU Torch/Transformers/PEFT). Verify RED/GREEN CI, independently review optimizer schema compatibility, then run broader suite and prepare a newly registered native continuation diagnostic without rewriting original failed evidence.
