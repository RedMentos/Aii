# WP-T8 World-model held-out support leakage — independent review 2026-10-27

**Owner:** GPT-6 continuation, review-only child of PR #739 exact `fa76ea437b26a161a2e21c17dee575811cc0eda0`. Preregistration `b450bff9d34f59fef812652df95ff397571f6f69` and persistence amendment `d766ea8dd376570c8490478f7f7d72db78dbccfc` preceded source changes; additional boundary amendment `cbb7df781908d0a858a9c867cad0c94ddbe5305c` preceded the second patch.

## Defect

`world_model.fit` computed held-out metrics using train/test split but populated `states` for counterfactual coverage from **all** rows. A held-out-only action therefore appeared supported by its own held-out observation, artificially reducing OOD distance and inflating simulation confidence. Old persisted `t8-world-model-v1` states carried the same contamination and could remain active after a code-only fix; public `counterfactual(..., st=legacy)` also bypassed `load()` validation.

## Repair

Revision `t8-world-model-v2` invalidates old stored v1 fits until explicit refit; `states` is constructed only from `tr` rows, truncated to 256 per action as before. New `support_counts` reflects actually retained training support, `train_counts` reflects all training rows; `counts` preserves the historical all-observed total. `counterfactual` rejects a directly supplied wrong-revision fit. Original split, model parameters, seed, ridge/ensemble, targets and held-out metrics remain unchanged. No Age/learning authority, native model, production runtime or Redmi change.

## Evidence

RED test-only commit `44b1f5f83d6b4b719bb0bbd45b907541993d5692`, Actions `40533408641`: **7 tests, 1 expected FAIL** (held-out-only `both` action incorrectly present in support), 6 PASS; INSTALL/COMPILE/PRIVACY/DIFF exits 0, UNIT exit 1. Original artifact `12746398241`, ZIP SHA256 `bf7e35f5609c754cb2a53be2b59c8d4367899b853a070cd3085af6ceb77ecd05`; CRC, HEAD, source blob, raw exits and failure inspected. Private Library backup byte-identical at `/V13-Checkpoints/2026-10-27/Automation11I-World-Heldout/RED-40533408641.zip`.

First GREEN source `4acdaeeb70e029e1b7d97825a00750d11862875c`, blob `c9c11346272aca3debc601bed9cae4ed877e5441`; subsequent independent review tightened direct-v1 and support-count contracts at `3802440b7e80ff245ad1c547e7ed650848e8519b`. Latest test source `acce97eb4e8e79a2cc1501799e0feb78358c2f79`, World-model blob `ff82c266a499fb7f59bd92a0fa60ed557a0dfc5a`: focused Actions `40533900523` **9/9 PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF all exit 0, artifact `12748170445`, ZIP SHA256 `9ef6642770ccd79484d6a771d394bc79fac2f3edb3fd9929c8858c5b49c58d9d`. CRC, exact HEAD/source blob and raw exits independently verified; private Library backup byte-identical at `/V13-Checkpoints/2026-10-27/Automation11I-World-Heldout/GREEN-40533900523.zip`. Latest exact-source full software suite **PENDING**; do not promote from prior full-suite runs. Inspect exact-head Actions and close raw evidence before any PASS claim.

## Negative gates and next

LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL; `jepa_weight=0`, Age authority 0, Redmi unmeasured, whole V13 incomplete. This is a synthetic/software confidence-integrity repair, not learned causal World-JEPA utility. **Next:** verify latest exact-head focused/full-suite raw exits and private backup, then independently review training-only support and direct legacy-state rejection; no automatic main merge. Pursue distinct blueprint work after verified checkpoint.
