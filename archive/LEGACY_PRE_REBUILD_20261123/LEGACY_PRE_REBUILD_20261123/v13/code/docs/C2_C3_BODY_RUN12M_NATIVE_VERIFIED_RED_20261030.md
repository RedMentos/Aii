# Run12M — original disjoint C2/C3/B1/B2 native pilot PARTIAL RED (2026-10-30)

Owner GPT-6, review-only PR #1269 child of #1268. **No original Run11V, Run12L, scorer, seed, model or Canon changes.** Four new source-grounded arithmetic tasks × four Latin-square arms = 16 actual Linux-native turns. Preregistered before native, source fixture SHA256 `c2739d0e3a0a7e9bda8383e145a9c7c2cfa26d3ab86a7052030ff32679884b48`, seed181 inherited from frozen Run11V `fresh_turn`.

## Verified source and original raw

- Source-only Actions **41054685390 SUCCESS**, exact HEAD `0d35a36f7bf2e7f05fe930de44c9fdc0bea04cac`, **46/46 tests PASS**, 8/8 stage exits0, privacy CLEAN; artifact **12975308965**, ZIP SHA256 `cceaa5149cb9aa9b663ba6d9969f3304961221bd16867ae1f4dd3f945010aa8b`, 5,152 bytes, CRC PASS, 18/18 inner hashes, private Library backup byte-exact.
- Genuine serial four-model Linux-native Actions **41054908080 FAILURE**, exact tested HEAD `faf0e6c6717ff8a80d0163e13f2836d399c356dc`; **9/10** stages exit0, `NATIVE_EXIT=2` (scientific structural RED, not bootstrap failure), `REPORT_CHECK_EXIT=0` (independent verifier faithfully confirmed RED), 46/46 source tests PASS, model bootstrap successful, privacy CLEAN. Original artifact **12976826165**, ZIP SHA256 `2203a2d757db084f3b79244433af92fbf01ad8dd1cd555b80a986ae2e7df9b55`, 264,497 bytes, CRC PASS, **60/60** inner hashes. Independently re-read **16/16 original raw**, **16/16 preclose witnesses**, **4/4 strict admission files**, verified HEAD, model pins, score totals, negative gates. No row discarded.
- Private byte-exact Library backups: `/V13-Checkpoints/2026-10-30/Run12M-C2BodyUtility/V13_Run12M_PREFLIGHT_41054685390.zip` and `V13_Run12M_NATIVE_RED_41054908080.zip`; original ZIP re-materialized and byte-compared.

## Negative result and exact structural reason

All **four F_NATIVE_AUTO turns actually invoked native C2**, and strict unique-tool admission replay matched **4/4**. Two advisories selected a non-simple route. **14/16** turns met the frozen Run11V full native/output/observer/release witness. The other two (Meridian197/F and Solstice197/F) fell back to `simple` after malformed or ambiguous C2 tool output, but the F arm's **background observer still generated a B1_DETAIL offer**. The frozen `row_evidence` expected zero offers for final `simple`; therefore `process_release_valid=false` and `valid_native=false`, even though native C2 invoked/reaped, C3 final output was generated and after-close releases were recorded. This is an **observer/route-arm design confound** in the frozen experimental witness, not proof that native execution crashed. Preserve it as RED; do not retroactively relax the original rule.

Conservative original primary scores (out of 8, invalid rows score zero): C3-only **0**, B1-only **5**, B2-only **4**, F native-auto **1**. Original secondary strict scores **0/8 all arms**. These are descriptive and incomplete for the two F invalid rows; **no complete-cohort comparative utility claim** is permitted. The preregistered F > best single +2/8 signal **FAIL** and all production gates remain negative.

## Next concrete package

Preregister a **new disjoint cohort** that isolates C2 route choice from observer effects: use observer OFF in **all** paired route arms, keep exact source/model/scorer pins, and validate the final selected native role + process releases with a new *prospective* witness appropriate for observer OFF. Include a matched C3/B1/B2 baseline and strict C2 admission proof. Do not rescore or rerun Run12M as if its original frozen witness had passed. Only after source-only tests GREEN launch one serial native job. Independently evaluate Needle's structured-extraction enum route option (official upstream docs) as a separate, nonintegrated candidate.

Age0 `RECORD_ONLY`, STEP2 `UTILITY_FAIL`, B3 `NO_PROMOTION`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, whole V13 incomplete. No production runtime/route/weight changes.
