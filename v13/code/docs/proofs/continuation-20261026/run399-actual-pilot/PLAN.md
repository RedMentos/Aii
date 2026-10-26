# Run399 — observed Run395 native artifact independent postflight

2026-10-26. Owner: GPT scheduled continuation. Base: Run398/PR393 exact head `1927d1931a0d90a6a0502fdec9d61218d326037d` (stacked review; not main). Own only new `.github/workflows/run399-step2-actual-native-postflight.yml` and `v13/code/docs/proofs/continuation-20261026/run399-actual-pilot/`; do not mutate frozen Run394/395/396/397/398 sources or their cohorts.

## Observed input, not a guessed artifact

Run395/PR390 native job `121333557565`, workflow `40247992605`, exact head `48d2119dbbc7077da10b625ca4ff5819bfc74730`, completed SUCCESS at 2026-10-26 00:33:08Z. Observed artifact ID `12619659510`, ZIP SHA256 `6a0ae4311db51d7165e372b370e57a6faf8223c0e214c87be5f6e1ad5ba46b6f` (457693 bytes). A separate local downloaded copy matches this SHA; ZIP CRC, all 35 manifest entries and six zero prerequisite exits were checked before this plan. Local source-neutral preliminary inspection shows 42 claimed native rows, O/P/S x seed20, and all three arms explicitly `UTILITY_FAIL`. Do not mistake this for independent Run396 postflight yet.

## Implementation and verification

1. Add a PR-triggered, read-only exact-artifact workflow using observed immutable ID+SHA (no inference, no model downloads, no paid provisioning), checkout exact PR head and verify frozen source hashes.
2. Run Run394/396/397/398 source controls, Run398 actual artifact auditor on the downloaded ZIP (which invokes Run396), privacy scan, and hash-close/upload every raw log and JSON including failures. Check `RUN399_NATIVE_AUDIT.json` status and 42 verified rows; source-only tests cannot substitute for actual ZIP.
3. Record exact GitHub Actions run/job/artifact IDs, raw SHA, structural result and paired utility, then independently review edge cases before any new native full-cohort decision.
4. Do not promote STEP2, B3, Body-JEPA/jepa_weight, Age or Redmi; preserve `canonical_architecture_complete=false` and `user_full_scope_complete=false`.

## Fail-closed

If the artifact cannot be fetched, SHA differs, raw manifest/rows are invalid, or the postflight fails, preserve RED and all raw, diagnose without changing frozen data. Do not rerun Run395. Source owner Run395 is complete; Run399 only reads its archived artifact.

## Next after verification

Compare observed O/P/S paired outcomes and determine whether the registered full 378-row cohort is warranted within native budget; if blocked, proceed to independent canonical blueprint implementation packages.