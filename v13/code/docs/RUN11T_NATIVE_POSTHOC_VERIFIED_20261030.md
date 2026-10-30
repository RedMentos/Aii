# Run11T — independent original Run11R native RED replay (2026-10-30)

**Review-only; no automatic merge or gate promotion.** Parent Run11R PR #1247 at `3346063841bc9a96a167fe5edf43863a7f34688e`; this child changes only the synthetic verifier test fixture, adds one ambiguity negative test, isolates synthetic primary/secondary totals, and runs a new source-pinned posthoc workflow. Frozen seed163 cohort, native runner, models, source, scorer, original output bytes and Canon are unchanged.

## Original evidence and failure retained

- Original real Linux-native Run11R Actions **41035932580 RED**, exact HEAD `3d76c8e28735cfef4d40c290baad4556b61e04a7`, artifact **12967698710**, ZIP SHA256 `47493d719ac1d6dedcb0142106b29b96817c0d4a211a6a2219879dec93cc8c5e`, **469247 bytes**, 73 entries, CRC clean, **72/72 inner SHA256 hashes**. All original PINS/VENV/DEPS/TEST/BOOTSTRAP/NATIVE/COMPILE/PRIVACY/DIFF stages exit0; original `REPORT_CHECK_EXIT=1` with `SOURCE_SCORE_REPLAY_MISMATCH`. This workflow remains RED and is **not** retroactively rewritten as GREEN.
- Parent posthoc Actions **41036791173 RED**: 29 tests, 1 synthetic test fixture failure. Both named equations on one line intentionally trigger the frozen equation scorer's dual-owner ambiguity.
- Child initial posthoc Actions **41037723812 RED**: 30 tests, 1 synthetic error `PRIMARY_TOTALS_CHANGED`; the synthetic fixture aliased primary and secondary totals to the same mutable dict. Both failures remain preserved.

## Corrected read-only verification

- Run11T Actions **41037868725 GREEN**, exact HEAD `f855313f28354dd570843001503301a6c32690a0`, artifact **12967434902**, ZIP SHA256 `98f50f8a624a4e7a914379798cafbd8484fdf2acb64063cfc2105da313a488a2`, **5398 bytes**, 22 entries, CRC clean, **21/21 inner SHA256 hashes**, all nine stage exits0, privacy scan **CLEAN**.
- **31/31 model-free synthetic/adversarial tests PASS**. Fixed only the test's equation-line ownership and independent primary/secondary totals, with explicit same-line ambiguity and independent-totals negative controls. The verifier's existing JSON-wire tuple/list normalization is unchanged.
- Source-pinned posthoc workflow re-fetched the **exact original native RED ZIP**, independently verified ZIP SHA, original HEAD, CRC and 72/72 hashes, then re-ran the current read-only verifier against **all 24 original raw rows**. `REPLAY_EXIT=0`, `PILOT_COMPLETE_NO_GATE`; 24/24 original rows structurally replayed. This is **posthoc software verification of original Linux-native raw**, not a new native run.

Original score totals remain exactly frozen:

| Arm | Primary / 8 | Secondary diagnostic / 8 |
|---|---:|---:|
| A_C3_ONLY | 0 | 0 |
| B_B1_ONLY | 0 | 2 |
| C_B2_ONLY | 0 | 7 |
| D_DISTINCT_BOTH | 0 | 1 |
| E_SHARED_DUAL_COLD | 0 | 0 |
| F_NATIVE_AUTO | 0 | 2 |

Original native C2 invocation **4/4**, native C2 route selected **4/4** in the F arm; this is evidence of route invocation/selection, **not** proof of better answers. Primary scorer **0/48**, secondary diagnostic **12/48** across all arms; disagreement is a measurement limitation, not a retroactive gate rescore. No comparative complementarity or response utility proven. The original `PILOT_COMPLETE_NO_GATE` is structural status only.

## Integrity, ownership and continuation

- Owner: GPT-6, Run11T review branch `assistant/v13-run11t-native-posthoc-testfix-20261030`. No edits to parent PR #1247, no force-push, no frozen model/fixture/scorer/hash modifications. Original failed attempts and parent RED are preserved.
- Private original native ZIP is already in Library `/V13-Checkpoints/2026-10-30/Run11R-C2Body-Closed/NATIVE_RED_41035932580_sha47493D.zip`; new Run11T GREEN and RED posthoc ZIPs must be byte-reverified in private Library before claiming secondary backup.
- Age0 `RECORD_ONLY`, STEP2 `UTILITY_FAIL`, B3 `NO_PROMOTION`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, whole V13 incomplete. Existing unfiltered historical Run34/Run37 source-pin RED remains; no waiver.
- Next: independent review of scorer mismatch and original 24 outputs, then **new preregistered disjoint paired** model-output utility study with A/B/C/D/E/F controls and frozen scorer plus separate diagnostics. Do not tune or rerun seed163. Continue independent JEF/ContextOS/JEPA/Sleep work in parallel. New Redmi proof still requires the user's device.

Verified next command: inspect GitHub Actions `41037868725` artifact `12967434902` and original `41035932580` artifact `12967698710`, compare exact hashes above, run `python v13/code/scripts/c2_body_observer_closed_verify_run11r.py --pilot <extracted-original>/pilot` on a checkout of the child branch. Do not replace original native raw.
