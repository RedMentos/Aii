# Run117DB integration prereg — combine C3 native schema-ablation and live Store source recheck

2026-11-01 UTC. Review-only child of Run117DA `9d7844e8eb21aa3ef0e2bd69c2cb2052f0184f84`, with independent Run117CW/CY source branch `b17515cc96eb0678a4ab0968d849dd439228e0c0`. This prereg is committed **before** copying files or running integration CI. DA native Actions 41262827609 owns the heavy runner; do not mutate its source, launch another native job or cancel it.

## Exact authorized integration

Copy the four **unchanged Git blobs** from verified Run117CY: `v13/jef_c3_source_callback_shadow_candidate.py`, `scripts/run117cy_live_source_native.py`, `tests/test_run117cw_c3_source_callback.py`, `tests/test_run117cy_live_source_native.py`. Preserve original blob hashes and code behavior. No modifications to Run117DA fixture, prereg, native runner, frozen Canon, production Runtime, models or source hashes. No native job in this package.

Test both paths in one source tree: 12-case Run117DA real SQLite F1/F5/JEF source-only schema ablation preflight + 48-arm synthetic runner controls, Run117CW real Store source mutation/revocation/side-effect veto, Run117CY single real Store synthetic runner and fake-native-proof veto, and prior Run117CU/CM source-only tests. Validate source blobs match originals, no oracle leaks, all negative gates unchanged. Original unfiltered Run117CT full suite RED 5,445 tests/2 immutable historical source errors remains binding.

## Limits

This combines **review-only experimental code** in one branch, not a production merge or new native proof. Run117CY already measured 1/1 Linux-native real Store callback FINAL/reaped but output NONE vs A (utility 0/1). Run117CX native capacity both models 3/9 all NONE. Run117DA disjoint schema native still PENDING. Any future production C6 output requires an atomic commit-time source authorization, human approval and independent utility; a post-generation recheck alone is not sufficient.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no native Body/JEF/C2 or Redmi/whole-system promotion. Preserve original raw and private backups. Review branch only.
