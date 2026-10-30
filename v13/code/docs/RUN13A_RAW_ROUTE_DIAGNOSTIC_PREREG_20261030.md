# Run13A original-native ZIP exploratory route diagnostic — posthoc, no rescoring (2026-10-30)

Owner GPT-6, review-only child of native Run13A #1280 at 5ba394d08ab9494d77f0b406b74ea931532b0388. The original private ZIP was located in the user's authorized private Library and materialized read-only: SHA256 52b1e6c8209dba364f41a157496cccfd9d59590e84e79139879ad87e5f576a6f; 97 entries, CRC clean; original HEAD 57cb8215ac95484e86a7e9bf1d1d2977aa6a4a35. This is explicitly **posthoc** exploration of an already frozen failed pilot, not a new preregistered scoring experiment.

Observed facts before coding: F_NATIVE_AUTO selected C3 five times, B1 three times, B2 zero times; three native route changes yielded route 'both' and C5's BOOT prior maps 'both' to B1. C2 returned multiple function calls on several rejected rows. Original frozen F numeric 0/16, strict 0/8; B2 numeric 6/16, strict 2/8. On Summit211 F output, both expected remainder numbers appear in text but frozen scorer recorded 0; text also states the wrong faster option. Mere numeric presence is not semantic correctness and must NEVER be reclassified as a pass in this diagnostic.

## Implementation acceptance

- Standalone read-only CLI accepts an original ZIP; reject wrong outer SHA256, unexpected/unsafe names, missing/extra SHA256SUMS entries, CRC mismatch, wrong HEAD, report fixture/seed/arm order or negative gates. Never extract or execute archived files. Retain original failures.
- Compute per-fixture F selected role/route, C2 raw call count and rejection flag, original F/B2 numeric and strict outcomes; emit output text hashes and two **value-presence flags only**, with an explicit no-rescoring disclaimer. No raw model text in public summary.
- Synthetic test fixture exercises exact manifest verification, tamper rejection, original scores preserved, value presence not treated as correctness, and no text leakage.
- Run CLI locally against the original private ZIP, save the sanitized analysis privately with SHA256 and independent source hash; source-only GitHub Actions tests synthetic fixtures, compile/privacy/diff/Canon.
- Never change frozen Run13A fixture, model/source pins, outputs, score thresholds or registered cohorts. Any prospective new scorer/route intervention requires disjoint preregistration and a new native cohort.

Gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete. Exact next command: implement read-only ZIP analyzer and synthetic tamper tests, run private original replay, then source-only CI and remote checkpoint.
