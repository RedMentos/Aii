# P2X 360-call calibration native result — independent original raw replay (2026-10-29)

Owner: GPT-6 isolated review PR #1080, parent PR #1079. Original independent prereg `00542f5536830dfa0b7cc281d227b73a02faf14e` was committed while native run 40862592051 was still in progress, before any model outputs were read. **No new model calls, training or production merge** in this review.

## Original RED preserved, then exact repair

- First [Actions 40863315508](https://github.com/RedMentos/Aii/actions/runs/40863315508) **RED**: downloaded exact original native ZIP SHA256 `0cef7a72655ba4e58c15ca52b0189e2bdd0b90c3f58daa69e22da2b12259d9d9`, verified CRC, **29/29 inner SHA256SUMS**, **11/11 original stage exits**, and original head `977d1b3bd8b1d54bd672ae30948a14e734e4463c`. Standalone verifier then failed **before reading model-output scores** because its CLI PYTHONPATH omitted the `scripts` directory needed by `p0x_independent_source_holdout` import. Original RED ZIP SHA256 `a05c4ec4cb50c11862354422d7eb4d1a76535fe16a9ba9cdd58fbfc136fcfa52` privately backed up byte-identical. Prospective addendum `P2X_CALIBRATION_INDEPENDENT_IMPORT_ADDENDUM.md` committed before dependency-only workflow repair.
- Corrected [Actions 40863448309](https://github.com/RedMentos/Aii/actions/runs/40863448309) **GREEN**, exact head `2705b2efb1218732b28afd2fb87785d2c96cea7a`, original audit ZIP SHA256 `b3eb4e38257e9ea43687629331cf24513def10601be03f435c105c73ac447490`, CRC CLEAN, **22/22 SHA256SUMS**, **11/11 audit stage exits zero**. Downloaded and independently verified the same original native ZIP, original 29/29 hashes and 11/11 exits; independent replay **360/360 raw records**, 36/36 oracle identities, all output labels, all per-arm counters and receipt/score hashes matched exactly.
- Corrected independent source-only [Actions 40863466702](https://github.com/RedMentos/Aii/actions/runs/40863466702) GREEN: **24/24 adversarial tests**, standalone CLI import check PASS, 14/14 hashes, 6/6 exits, privacy CLEAN; original ZIP SHA256 `00039ddd675fcc6814e277de126c13eef82e501bc8a0809a7c31d0df3cb91615`. Original 24-test [40863066134](https://github.com/RedMentos/Aii/actions/runs/40863066134) also retained. All original audit ZIPs privately backed up byte-identical at `/V13-Checkpoints/2026-10-29/P2X-Calibration/`.

## Independently recomputed paired changes

| Source arm | Improved (wrong→correct) | Regressed (correct→wrong) | Both wrong | Both correct |
|---|---:|---:|---:|---:|
| c3_only | 36 | 0 | 0 | 0 |
| b1_only | 36 | 0 | 0 | 0 |
| b2_only | 36 | 0 | 0 | 0 |
| both_exact | **0** | **12** | **24** | 0 |
| shuffled | 36 | 0 | 0 | 0 |

The original source-only format produced NONE for all 36 `both_exact` calls (12 exact by matching the NONE oracles); the instructed format produced UNKNOWN for **all 180** calls. The 144 negative-arm improvements are therefore a **constant abstention** result, while the complete-source arm regressed by 12/36. There is **no evidence of C3 source-availability discrimination or A/B/NONE reasoning**, despite reliable grammar-constrained output and intact source transport. These are public synthetic calibration rows, not independent held-out utility or trained adaptation.

Original raw `RAW.json` SHA256 `cc8221f33fb5d30515aafcb9bbd4312e00f820f89c5ee1d3ef78123eac4c3bc8`, `SCORE.json` SHA256 `9436147589763695881b764b340b0d8881c3962c30816b5b8d985c8884d13ed6`. A separate local independent **source-text** parser reconstructed all 36 calibration oracles from exact B1/B2 prompt text and checked 360/360 outputs without importing either scorer, providing a second distinct replay path.

Full integrated software regression [Actions 40862737502](https://github.com/RedMentos/Aii/actions/runs/40862737502) GREEN: **3,074 tests OK (11 skipped)**, 16/16 focused, 16/16 hashes, 7/7 exits, privacy CLEAN, original ZIP SHA256 `f29a40a31d012ac883f458eff3ef6e0033d977d96dd1aa85f0b2dd79e9f30ab6`, private backup byte-identical. This proves source compatibility, not native utility.

**All gates remain negative:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. No production merge.
