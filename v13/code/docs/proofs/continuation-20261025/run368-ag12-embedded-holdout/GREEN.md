# Run368 GREEN — embedded AG12 holdouts excluded from distillation

## Verified source changes
- Parent Run367/PR362 measurement branch `9df12a9d9032805aab7921da9b6c104ccfb3e654`, review PR #363, **not merged into main**.
- `v13/code/v13/agi/generality.py`: `guard_training` now rejects a registered unseen task embedded verbatim (after case/whitespace normalization) anywhere in a training text, while retaining original whole-text hash checks and the immutable registered suite.
- `v13/code/v13/agi/teacher.py`: dataset checks every field actually handed to distillation — request prompt, target, reasoning and rejected earlier answer — rather than prompt alone. A safe local fake teacher trace remains usable.
- Production SHA256 `generality.py` `66d089ea1b2d474029f55e42b611e9030501a140ea216eedd90b7289b931e56c`; `teacher.py` `4ff84014b4bdc8560f32675852f62ef4158251f47d4cc064b29bf6c23fd4df32`; final test SHA256 `bbc4254356d68a278da6dd7cc59993f1f10fef58405bd97c59ca30e526ce0563`.

## RED/GREEN and raw evidence
- Prereg PLAN commit `e3db9c85c1d307dc47f8ca7a85231446880f8345`; test commit `1661a5d3558d7861940f7a05cb9e44d62ae603c5` preceded production patch.
- RED exact checkout `8f3ab1b7053714b3f157307034ddea85839c9531`, Actions `40232384911`, job `121286672401`: **35 tests, 6 expected assertion/subtest failures**, inherited 30 AG12 tests PASS, privacy CLEAN. Raw ZIP artifact `12612934100`, SHA256 `714e3d8439b27b833f9f3f6240913c1d0c7a804b218ee5d009f2b9d54b149704`.
- First GREEN `7331fe126ef274c1244f10e44ad5baf58ec28e05`, Actions `40232468737`: **35/35 PASS**, privacy CLEAN, raw ZIP SHA256 `c0f55ba14240fb4d107b9ba2313f530afe40757350167237d70e150df7ab5b9a`.
- Final independent hash-preservation regression `501a9f18aa0cdb8889b84344d85d6617d3dfc83f`, Actions `40232602273`, job `121287330070`: **36/36 PASS in 2.192 s**, compileall PASS, privacy CLEAN. Focused source-bound workflow `40232602281` SUCCESS. Final raw ZIP artifact `12613793107`, SHA256 `3fd2adb55842d8e0eb780ad05ec14f59d520be85474a6c1a0e5bd5eb4fd401c8`.
- All three downloaded raw ZIPs passed CRC and internal 4/4 member SHA manifest checks. Private Library uploads for RED, initial GREEN, final GREEN at `/V13/checkpoints/2026-10-25/`; each was re-materialized and byte-compared with its original downloaded ZIP:
  - `V13_Run368_EmbeddedHoldout_RED_raw_sha714e3d84.zip`
  - `V13_Run368_EmbeddedHoldout_GREEN_raw_shac0f55ba1.zip`
  - `V13_Run368_EmbeddedHoldout_GREEN_FINAL_raw_sha3fd2adb5.zip`

## Negative gates / next
- Registered suite hash and stored holdout digests remain unchanged by the guard (actual SQLite regression). This is **exact normalized substring** exclusion, not a semantic/paraphrase leakage proof.
- Evidence = synthetic source/SQLite; no native model, Redmi, real learning gain, STEP2/B3/Body-JEPA/jepa_weight/whole-system promotion. `canonical_architecture_complete=false`, `user_full_scope_complete=false`.
- Next: close Run367 exact-head full-suite raw result and classify any surviving historical failures; then select an independent canonical functional package or pinned native probe, preserving active owners and negative gates.
