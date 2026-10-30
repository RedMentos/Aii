# Run13Z prereg — AG9 source-disjoint heldout calibration shadow (2026-10-30)

Owner GPT-6, isolated review-only child of Run13Y `1096d953252811652f0e602980c745529ad7a25a`. WP-AG9 / WP-DS3: current `Metacognition._fit` and `age_metric` use the same observed examples to fit and report calibration, so in-sample ECE can be optimistic. No evidence currently authorizes Age advancement; BUILD_CEILING=0. This adjacent diagnostic does not alter the existing AG9 store, calibrator, age metric, or production routing.

## Precommitted test and verdict

Implement pure, no-write, source-disjoint `audit_heldout(train, heldout)` using existing exact AG9 PAV calibrator and existing generality ECE/Brier scorer. Require train >=20 and heldout >=10, exact row schema `{source_id, confidence, correct}`, globally unique nonblank source IDs, finite nonboolean confidence and exact bool/int0/1 label. No training/heldout source overlap; no external data; no model/native calls. Calculate raw and calibrated heldout ECE/Brier and training ECE/Brier. **HELDOUT_DEGRADATION** if heldout calibrated Brier > heldout raw Brier + 0.02; otherwise **HELDOUT_NONDEGRADATION_SHADOW**. The diagnostic verdict never authorizes Age promotion, even if heldout appears better. No model weights or existing AG9 state writes.

Counterexamples: training data where confidence predicts outcomes but heldout reverses the relation (in-sample ECE misleading), heldout matching control, duplicate source IDs across splits, malformed labels, NaN/Inf, insufficient support, and monotone table. Tests must preserve unchanged Canon, all negative gates and frozen model/seed/scorer cohorts. This is synthetic software diagnostic only, not a real semantic calibration/utility proof, STEP2/B3/Body-JEPA/JEPA/Redmi or whole-system acceptance.

Checkpoint and review on this child branch, preserve raw tests/hashes, private backup if possible. GitHub Actions queue currently pending on prior Run13X/Y jobs; no claimed remote CI until terminal. Exact next command: implement isolated module and tests, execute local exact-source mirror and independently verify remote bytes, then GitHub source-only CI when runner is available.
