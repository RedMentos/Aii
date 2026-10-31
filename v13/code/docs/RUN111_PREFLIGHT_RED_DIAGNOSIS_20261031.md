# Run111 first preflight RED — immutable diagnosis and correction plan

Original Actions `41213687065` exact tested HEAD `2455e38c76357de61531dfec613dfc98ca004c56`, terminal FAILURE. Original artifact `13047227796` 15,148,845 bytes SHA256 `a236a519a8c01fdd219e48a4b1c8ca67fa0203516144a88e2069b6e7408230ac`, CRC PASS, 27/27 inner SHA256SUMS PASS, original HEAD matched. Private Library `/V13-Checkpoints/2026-10-31/Run111-Preflight/ORIGINAL_RED_41213687065_SHAa236a519.zip` independently re-materialized byte-identical.

Two exact REDs, not hidden:
1. New test expected every `verified_quote` to start with `Maximum budget:`; in WIDE arm original Run102 contract correctly returns the **full prior source**. The direct real Store/Context OS preflight itself PASS (8/8), original Run102 context tests 3/3 PASS. Correct test expectation by arm: WIDE equals frozen `prior`, NARROW equals frozen `quote`. Do not change source fixture or `analyst_context`.
2. ZIP verifier demanded `docs/fixtures/RUN111_C3_PRIOR_RULES_SEED881.json` inside phone ZIP; original `package_source.py` intentionally excludes arbitrary `docs/fixtures` files, preserving small phone packaging. Keep preregistered fixture immutable in checkout, use it as external registered scientific input to extracted source for native run; verify its SHA independently. Do **not** weaken phone source ZIP integrity or add experimental fixture to production phone-required allowlist.

Correct only the test and ZIP workflow, retain original raw RED and rerun all original stages. Native C3 ablation remains blocked until corrected software preflight GREEN. No source/seed/model/runner/canonical gate changes.
