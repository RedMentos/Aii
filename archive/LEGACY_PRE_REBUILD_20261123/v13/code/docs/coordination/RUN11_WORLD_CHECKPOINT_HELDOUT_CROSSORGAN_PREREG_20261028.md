# World-JEPA checkpoint × heldout-action readout — independent cross-organ prereg (2026-10-28)

Review-only child of Run11 four-way integration PR #831 at exact `28320b825d789ecc4d505a2b86279bcb2fc89927`. Separate owner branch; do not modify parent or #828/#830. Preregistration precedes new tests/workflow.

## Test objective
Exercise a **real fitted** (12 NumPy training steps, seed 3, two predictors) SHADOW WorldJEPA on the existing synthetic 64-row file-world split. Compute correct and heldout wrong-action predictions and a **single frozen correct-action ridge readout**; save fitted model to a fresh private temporary NPZ with externally supplied source SHA256 and returned byte digest; load it back and assert exact latent, action-conditioned predictions, OOD, confidence, labels, readout MAE and action-mismatch sensitivity without retraining. Reject mismatched source SHA256 on restore. Test the public repository contains no private fitted NPZ.

No training resume, optimizer persistence, live runtime hook, human data, new cohort, model download or causal utility claim. Existing #828 negative utility and original registered cohorts unchanged. Synthetic only; no actual native models or Redmi. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY.

## Verification
Run focused new cross-organ test plus existing checkpoint/heldout-action tests on branch-only Linux CI with pinned NumPy 2.2.6, compile, privacy scan against parent #831 and diff check. Close raw logs/exit codes and source hashes. Any failure remains recorded; no gate promotion. After GREEN, independently review exact state transfer and update handoff with raw artifact hash. Parent full-suite CI must be independently checked; a passing focused test is not whole-system completion.
