# Run34 prereg — independent read-only audit of closed Run32 real-file W7

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run33 #1360 at `5370b56d5ca6e5f057d0c884aee68ec308769548`. Run32 original source HEAD `550185a74e9daddaea27860f6244c1209d376af2`, Actions `41146711268`, original artifact ID `13021771958`, ZIP SHA256 `adda55e8d4d4fd5aabd328b8f79d03c08d2b6804fb2c48daea4043f1052faecb`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Run32 seeds 201–203, 4000/150/300/3000, original 16D versus slot 96D, original frozen W1–W6 and W7 thresholds unchanged.

Before this prereg: original ZIP independently downloaded; CRC PASS, 130/130 inner SHA256 manifest members, all nine stage exits 0. Original result reports **SHADOW_CANDIDATE_FAIL**: original W1/W4/W5/W6 fail, slot W6 fails; W7a PASS, W7b/W7c FAIL. The source workflow's report is not a substitute for an independent read-only recalculation.

## Frozen independent audit plan

Implement stdlib-only `run34_world_jepa_disjoint_raw_audit.py` taking original ZIP path and a fresh aggregate output path. Fail closed on outer SHA, CRC, missing/duplicate/extra manifest entries, bad inner hashes, any stage nonzero, wrong source HEAD/seed/cohort/schema, missing six per-seed checkpoints, nonfinite values, unexpected gates or false evidence labels. Verify each per-seed checkpoint matches its corresponding top-level arm after removing diagnostic-only `_conf_err`; recompute W7a/b/c per seed and mean from original stored attribution rates with original thresholds (>=.20/.10; >=.05/0; >=.08/.04), verify minimum class count >=15, and compare the stored W7 summary to independent calculations within rounding tolerance. No modification of raw, model, seed, source or registered criteria; no retrospective threshold tuning.

Output only aggregate PASS/FAIL diagnostics, hash provenance and negative gates, **never** the raw file-world content. Unit tests cover correct derivation, tampered hashes, malformed/missing/duplicate manifests, W7 false-positive attempt, missing seed, nonfinite, stage failure and negative-gate mutation. Execute actual original ZIP with the same script on Linux (read-only); CI can retrieve original artifact without heavy model jobs. Preserve original failed evidence, source and synthetic data in permitted private Library, not public GitHub.

## Scope

A passed audit validates evidence integrity and an exploratory W7 failure, not JEPA utility or model learning. Matched-capacity controls and stronger world-only/own-only interventions remain independent next work. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, no Redmi or whole V13 completion.
