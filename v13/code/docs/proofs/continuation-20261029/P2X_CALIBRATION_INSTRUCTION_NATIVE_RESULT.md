# P2X C3 one-factor explicit source-instruction calibration — Linux-native result (2026-10-29)

Owner: GPT-6 isolated PR #1079; **not production merged**. Prospective prereg commit `9352843a7ef6fb0eb7cc3307b98f12501e9685c2` preceded implementation and all new model calls. Parent frozen 72-ID validation #1078 remains unchanged and negative.

## Original native evidence

- [Actions 40862592051](https://github.com/RedMentos/Aii/actions/runs/40862592051), exact workflow head `977d1b3bd8b1d54bd672ae30948a14e734e4463c`, GREEN execution; **negative source-use utility**. Original ZIP SHA256 `0cef7a72655ba4e58c15ca52b0189e2bdd0b90c3f58daa69e22da2b12259d9d9`, CRC CLEAN, **29/29 inner SHA256SUMS**, **11/11 stage exits zero**, source/privacy/diff CLEAN. Original ZIP privately backed up byte-identical at `/V13-Checkpoints/2026-10-29/P2X-Calibration/NATIVE_GREEN_40862592051_sha0cef7a72.zip`.
- Exactly **360/360 real Linux-native QAD C3 base-only calls**: 36 calibration IDs × five source arms × two prompt formats. Frozen generator Git blob `8135fa2792df2c541dc1719e49d941c775703697`, fixture SHA256 `cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`. No P2X validation IDs, no P0X holdout, no adapter, no training, no system activation.
- QAD GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; pinned llama.cpp b10964 archive `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; extracted binary `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`; seed13, same constrained JSON schema, same sampling and token budget. Mean Linux call duration **0.577 s**, max **0.858 s** (not Redmi).
- `RAW.json` SHA256 `cc8221f33fb5d30515aafcb9bbd4312e00f820f89c5ee1d3ef78123eac4c3bc8`; `SCORE.json` SHA256 `9436147589763695881b764b340b0d8881c3962c30816b5b8d985c8884d13ed6`; `INPUTS.json` SHA256 `f78d99713325f318fd296f3d1e53132066b591b37318277f771852e558816602`. All 360 outputs FINAL; native process reaped; model/runner hashes unchanged.
- Independent **local source-text oracle reconstruction** from the 36 model-facing `both_exact` prompts, without importing the original scorer, reproduced **12 A, 12 B, 12 NONE** and independently re-parsed **360/360** strict JSON outputs and original detail labels. Separate independent GitHub Actions raw audit #1080 is in progress and not yet counted as GREEN.

## Observed result — no source-sensitive decisions

| Source arm | Original exact / 36 | Instructed exact / 36 | Instructed behavior |
|---|---:|---:|---|
| c3_only | 0 | 36 | UNKNOWN 36 |
| b1_only | 0 | 36 | UNKNOWN 36 |
| b2_only | 0 | 36 | UNKNOWN 36 |
| both_exact | 12 | **0** | UNKNOWN 36 |
| shuffled | 0 | 36 | UNKNOWN 36 |

Original format returned NONE in all 36 `both_exact` calls (12 NONE oracles matched by constant answer). Instructed format returned **UNKNOWN in all 180 calls**, including all 36 complete-source cases. The system instruction eliminated negative-arm false commitments but **also eliminated every valid-source decision**. This is a trivial abstention collapse, **not** demonstrated source availability discrimination, learned rule use, or two-body utility. The one-factor comparison isolates the effect of the explicit system instruction *under this frozen grammar/sampler and calibration cohort*; it does not establish the general cause of C3 failure.

## Next substantive package

Do not tune on the frozen 72 validation IDs. A future independently preregistered training or structured JEF/Context OS decision consumer must show both (i) reliable UNKNOWN on missing/foreign sources and (ii) correct A/B/NONE discrimination on complete sources, with shuffled and single-source controls, before any new held-out evaluation. The existing P2X one-step LoRA pilot is not a deployed adapter and does not prove receiver utility; AG6 remains unapproved. Review whether a deterministic typed JEF consumer can provide immediate safe source-use utility while a genuinely learned C3 receiver is separately tested. No production runtime changes or gate promotion in this package.

**Binding gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE.
