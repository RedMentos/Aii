# Run12J — C2 Runtime native tool route admission (2026-10-30)

Owner GPT-6; draft PR #1266, child of #1265. Review branch only, no production merge or new authority. This patch affects the *existing* Runtime advisory path but does not widen native admission beyond simple-scaffold routes.

## Real source defect and fix

The original `Runtime._route` at Git blob `68e7ed1352800174972558f1e0b0683a42c8689a` recursively scanned any nested dictionary, list or JSON-looking string for a `route` field. It could therefore select a foreign diagnostic route before the actual `select_processing` tool result, and it could select a route even when the native result reported `success=false`.

Candidate `runtime.py` Git blob `22ed11e4a53d9eeae8fbc74a1753082b5785be2b` instead calls the already-existing `control_calibration_worker.observation` to validate native success, finite confidence, nonnegated/grounded output and recognized tool route, then requires **exactly one** `select_processing` call. Any ambiguity/foreign tool/nonfinite confidence keeps the scaffold. The existing calibration gate, explicit route override, source-bound executive control context and simple-only native admission are unchanged. No native model, weight or Age permissions changed.

## Original and fixed software evidence

- New seam tests `test_c2_route_runtime_strict_run12j.py` Git blob `cfacb8739c769c8a4171ce1d19eaa477d9528eb5`: valid unique call, foreign top-level route, failed native, ambiguous/foreign/nonfinite/negated calls, non-simple scaffold.
- Original-vs-patch independent reproduction on real `Runtime._route` method with fake Needle: **original foreign route `gist`**, patched validated tool `detail`; **original failed-native route `both`**, patched scaffold `simple`.
- GitHub Actions **41051158002** GREEN at tested HEAD `e2f15e823068a91e90df9ff6b6786694d30505e3`; **57/57** C2, calibration, benchmark and provenance software tests PASS; PINS/VENV/DEPS/TEST/COMPILE/REVIEW/PRIVACY/DIFF all EXIT0; privacy CLEAN.
- Original artifact **12974936511**, ZIP SHA256 `c24b39bca80909450c78cbac77503788cb996ea206c89305997042622ba22341`, 78,778 bytes, CRC PASS, **21/21** inner hashes. Private Library `/V13-Checkpoints/2026-10-30/Run12J-C2StrictRuntime/V13_Run12J_C2_41051158002.zip` re-materialized and byte-compared **EXACT**.
- Source pins: Runtime 22ed11e4, tests cfacb873, calibration worker 1b353cf7, Sleep 90d5361d, Canon 218464b1. Original failed controls are retained in raw; no rewrite of registered cohorts.

## Other completed independent package

Run12I broad Sleep cross-organ review Actions **41050891565** GREEN: all **89/89** named Sleep tests plus **3/3** Context/World/Sleep integration tests, original artifact **12973439878**, ZIP SHA256 `0ba7d064ec44ac22c199ad1159398d60cc80306263e0857e8c7ac354e793afe9`, CRC PASS, 14/14 inner hashes, privately byte-exact backed. This is software-only, not a full unfiltered suite.

## Limitations and next command

No genuine Needle3 native invocation in this Run12J patch test, no route task utility proof, no Redmi, no full-suite or whole-system acceptance. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, `jepa_weight=0`.

Next: independently run pinned Linux-native C2 with a disjoint preregistered source cohort and verify strict unique tool-call compatibility and actual route selection without changing the registered STEP2 cohorts. Continue other Canon work if native prerequisites block. Do not merge or promote from software-only evidence.
