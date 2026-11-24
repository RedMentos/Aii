# Independent WP-BJ1 / WP-BP2a body-JEPA input integrity review — preregistered 2026-10-27

Owner GPT-6, review-only child of Claude PR #701 exact head `1c9e8275caaca8bf58010ad3544cb2d3321352a5`; original BJ1_NO_SIGNAL and BP2A_PASS measured reports, weights, seeds and training scripts are unchanged. This review modifies only `v13/code/v13/body_jepa.py`, a new focused test file and scoped evidence. No production/age authority, no native retraining, no change to the canonical blueprint.

**Source-level RED hypotheses before patch:**
1. `jepa_loss(..., weights=[float('nan'), 1, 1])` returns NaN loss instead of rejecting; `weights=[inf,1,1]` similarly, and wrong-length eligibility is not validated.
2. `jepa_loss(..., mode='shuffled', perm=[0,0,0])` accepts a non-derangement with self-target and duplicates, corrupting the registered negative control.
3. `pad` permits empty sequences, and `last_token_latent` can index a zero-length row as -1 (last pad token), producing invalid target latent without refusal.
4. `minor_subspace_init` on a zero/NaN wrapped weight can produce NaN singular-mass metrics or silent invalid directions; rank bounds are not validated.

**Acceptance:** test first (RED on original source) with tiny torch-only fake body/wrapper, then add explicit finite/shape/derangement/sequence/rank guards; test GREEN with same source. Existing valid behavior and BJ1/BP2a measured conclusions must remain unchanged. Run inherited `tests.test_body_jepa` if compatible `peft` can be installed without paid provisioning, otherwise record exact dependency limitation. Compile, privacy, exact source lineage and negative gates. No native model run is implied by tiny torch tests. Do not merge production without Claude owner review.
