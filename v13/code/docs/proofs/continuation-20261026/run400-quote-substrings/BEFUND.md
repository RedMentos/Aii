# Run400 — native STEP2 pilot independent postflight after RED-first audit fix (2026-10-26)

**Source status:** GREEN, **native report audit:** `PILOT_POSTFLIGHT_VERIFIED` (42 actual Linux-native rows), **canonical STEP2:** `UTILITY_FAIL`. No Redmi measurement or weight learning demonstrated. Branch-scoped stacked review only; not merged to main.

## Exact immutable native evidence

Run395 native Actions `40247992605` job `121333557565`, source `48d2119dbbc7077da10b625ca4ff5819bfc74730`, completed SUCCESS 2026-10-26 00:33:08Z. Original artifact `12619659510`, SHA256 `6a0ae4311db51d7165e372b370e57a6faf8223c0e214c87be5f6e1ad5ba46b6f`, 457693 bytes. Independent download: ZIP CRC PASS, 35/35 raw member SHA256 PASS, six native/prerequisite exit files all 0. Native models/runner not rerun or modified.

Run399 exact artifact postflight `40250214439` job `121340253414`: **44/44 source-only tests PASS**, privacy CLEAN, actual audit **RED**: `B2 verified quote not exact frozen source`. Raw artifact `12620490121`, SHA256 `4dce2c14091064baab43add5c41093272e2d0023fa0d45559ef6dfc6e31a2ba5`, 14/14 raw SHA entries PASS. Preserved, not overwritten. Root cause: Run396 compared quote against entire history list items by equality, rejecting valid literal *substrings* of registered source. All 20 rejected B2 snippets in observed pilot are exact contiguous source spans; this does not by itself prove their usefulness or current-rule correctness.

## RED-first fix and independent GREEN

Run400 PLAN `d436aa4` preceded new tests `bdd7074`; workflow `683ab61` exact-head RED Actions `40250351938`, job `121340665410`: **51 tests, 3 expected errors** for exact historical/current source substrings; native audit remained RED, privacy CLEAN. RED raw artifact `12620710095`, SHA256 `7e9b9f0d75b4ab3b266e2ebacacbfd4db5b39f1afbde6442f5a371b3651c99fc`, CRC + 14/14 internal SHA PASS.

Narrow source fix `cb6bd9ee0038e4ae7ab43b53406f2ebc4b0f97a8`: require nonempty exact string quote wholly contained in **one** registered history/current source. Unsourced appended text, case-altered quote, empty/non-string still rejected. No native or frozen Run394/395 source, model, seed, fixture, tool policy or utility scoring changed.

GREEN exact-head Actions `40250408193`, job `121340840779`: **51/51 source tests PASS**, compileall PASS, privacy CLEAN, same original ZIP hash verified, **42/42 actual native rows verified**, `PILOT_POSTFLIGHT_VERIFIED`, zero postflight errors, zero wrong committed tool actions, all original `UTILITY_FAIL` and canonical negative gates preserved. GREEN artifact `12620144232`, SHA256 `4874a83b71737d5dfc990d6850f29c5305c5040d8a322ad0165b998eaef0c230`, ZIP CRC and 14/14 member SHA256 PASS. Private Library copies of RED and GREEN in `/V13_PRIVATE_CHECKPOINTS_20261024/Run400_Quote_Substring_20261026/` were materialized and SHA-verified byte-identical.

## Pilot utility — descriptive only, not a full-cohort claim

For `both_exact`, P (C-body with B2 pointer) minus O (same C-body pointer off) mean field-utility **+0.20833** over Alder and Delta: Alder **+0.41667**, Delta **0**. P minus S (D shared-body control) **+0.58333** mean: Alder **+0.41667**, Delta **+0.75**. `both_none` has the same paired means; `both_control` P−O **−0.08333** and P−S **−0.125**; `prompt_only_dual` P−O **−0.375**. These mixed outcomes and only 2 fixtures × seed20 do **not** isolate causality, establish statistical utility or pass STEP2. The full preregistered cohort is 378 rows, still unrun.

Historical B2 quote provenance: Delta O=2, P=4, S=0 exact old-rule spans. Such a quote is sourced but superseded by the current revision; never interpret as correct current action. Native output quality remains poor in several variants.

## Open / next

- Decide whether to run the full 378-row preregistered native cohort with Run397 append-only resumable runner after confirming measured budget and no competing native owner; pilot took ~23 min for 42 rows.
- Independently review native per-fixture failure patterns and source/candidate consumer packet paths; do not tune on this frozen pilot as if heldout.
- Continue canonical B1/B2/JEPA/C3/Context OS/JEF integration and Redmi proofs independently where native budget blocks.
- Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Run389 full suite RED, Age0 learning/approval restrictions, no Redmi phone proof, `canonical_architecture_complete=false`, `user_full_scope_complete=false`.
