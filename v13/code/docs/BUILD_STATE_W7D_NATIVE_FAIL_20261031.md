# W7D registered 701–703 real-file — scientific FAIL, engineering execution PASS (2026-10-31 UTC)

**Owner:** GPT-6 scheduled continuation; draft review-only PR #1421, child of D3 prereg integrity PR #1420. Original tested HEAD `9e432dd8255b0d718670c40247725d3a50bf2e74`. No production merge, no learning or age promotion.

## Frozen cohort and evidence

Original W7D prereg `WORLD_JEPA_DELTA_INVERSE_PREREG_20261031.md` and earlier independent D3 per-seed correction prereg preserved. Same paired real file rows for seeds **701, 702, 703**, train=4000, cf=150, attr=900, steps=3000, balanced six-slot vs delta-inverse arm, fixed source/model/Canon Git blobs. No posthoc retune, no source/cohort/model hash changes.

GitHub Actions **41175251034**, exact tested HEAD `9e432dd8255b0d718670c40247725d3a50bf2e74`, terminal **SUCCESS** means engineering stages ran, **not** that scientific utility passed. Original raw artifact **13031844870** ZIP SHA256 **`cd4983514cb67091225a3c309233a69cd7e159dc51ce43c378b3afc707fc88a0`**, ZIP CRC PASS, **80/80** inner SHA256SUMS entries verified, original HEAD receipt matches. All nine exit stages zero, 18/18 software tests PASS, privacy CLEAN, report checker PASS, real-file Linux x86_64 completed.

**Independent offline raw replay** using a separate NumPy double-argsort rank implementation, not the W7D candidate/evaluator: checked per-seed original RESULT files, class supports >=15, paired D1/D2, per-seed D3, original negative gates, exact cohort, 80 raw hashes and nine stage exits. Result: `INDEPENDENT_RAW_AUDIT_PASS_NEGATIVE_UTILITY_PRESERVED`. Reproducible posthoc read-only audit source `scripts/audit_w7d_native_raw_posthoc.py`, Git blob `d110bdbbd7498ed6e8cc521be14edcd4e1396ed2`; posthoc audit is not a new prereg or new scientific trial.

**Private byte-verified backup:** Library `/V13-Checkpoints/2026-10-31/Run1421-W7D-Native/W7D_NATIVE_RAW_41175251034_SHACD498351.zip`. Uploaded from original Actions artifact, then re-materialized from Library; SHA256 equals `cd4983514cb67091225a3c309233a69cd7e159dc51ce43c378b3afc707fc88a0`. No rejected anyone-writable Drive destination used.

## Scientific result: FAIL preserved

Both balanced and delta-inverse arms: **W1 PASS, W2 PASS, W3 PASS, W4 FAIL, W5 PASS, W6 FAIL; W7a PASS, W7b FAIL, W7c PASS**. Original status `SHADOW_CANDIDATE_FAIL`, not utility promotion.

| Exploratory prereg diagnostic | Per-seed deltas 701 / 702 / 703 | Mean | Outcome |
| --- | --- | ---: | --- |
| D1 W6 attribution margin | +0.0067, -0.0033, +0.0034 | +0.002267 | FAIL |
| D2 W7b none/self gap | -0.0558, +0.0584, -0.0531 | -0.016833 | FAIL |
| D3 per-seed W4 rho | -0.013768, -0.023847, +0.007962 | -0.009884 | FAIL |

Pooled W4 rho: baseline -0.1243 vs delta -0.1478, pooled change -0.0235 (diagnostic only). All prereg D1/D2/D3 failed; delta inverse is not a proven solution. Original W7S 601–603 FAIL and Run39 RED remain untouched.

**Negative gates:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, Redmi unmeasured, global 96D capacity control incomplete, whole-system incomplete.

## Next authorized substantive package

Do **not** rerun/retune W7D seeds 701–703 or relabel negative gates. Continue independent JEF operator policy/actual native structural integration in PRs #1422–#1424 and queued cross-organ full suite #1423. If exploring a different World-JEPA hypothesis later, preregister a genuinely disjoint cohort and new frozen candidate before observing results. Before new heavy native work, check group `v13-native-c3-ag12-20261030`; current Run66 native may be pending behind full suite. Exact independent audit command when ZIP available: `python v13/code/scripts/audit_w7d_native_raw_posthoc.py /path/to/original-raw.zip` with NumPy; retain failures.
