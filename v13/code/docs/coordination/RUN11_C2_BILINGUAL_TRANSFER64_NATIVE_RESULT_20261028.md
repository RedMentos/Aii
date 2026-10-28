# Run11 C2 bilingual transfer64 Linux-native result — 2026-10-28

**Status:** second, source-bound native run **GREEN**. This is a **negative quality finding**, not C2 promotion.

## Evidence chain and failed attempt retained

First run `40640185593` (source `ebef8885720553426bf614ec86fb6a943ab59b9a`, ZIP SHA256 `4db7a28829a87b362d8cf8611f66154cba8d424f544dc8ab49bccbfe1935bdcd`) bootstrapped pinned Needle but **BENCH=1** before any route call because workflow pre-created a no-overwrite output directory. All **17/17** internal hashes and private Library byte readback verified; original RED remains RED. Minimal workflow fix preregistered and committed without modifying the benchmark, fixture or model.

Second run `40640371815`, source `797da0a1a7c7965cb00504e8b10570696d500e80`, artifact `12795795465`, ZIP SHA256 `26cc4e5da5f1d2a9e93d224573de9957db0a25206b50cf2e62910f900b3eaa2a`: ZIP CRC clean, **21/21** internal SHA256SUMS verified, `BLOBS=GO=INSTALL=BOOTSTRAP=BENCH=REPORT_CHECK=PRIVACY=DIFF=0`. Native Needle model SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`, exact #850 benchmark/source, registered transfer fixture blob `e9aaae43f3313fbdc8e4b2fc870f2712a5557a66`, 64 ordered labelled rows. Artifact copied to **private Library** `/V13-Checkpoints/2026-10-28/Run11-C2-Bilingual-Transfer64/` and read back byte-exact at the same ZIP SHA256. No model weights/private user data published.

## Author-labelled route agreement (64 new, 32 EN + 32 DE)

| Route selector | Correct / 64 | Accuracy | Macro-F1 | English correct / 32 | German correct / 32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Needle3 native C2** | **19/64** | **0.2969** | **0.2837** | **10/32** | **9/32** |
| **Current regex scaffold** | **42/64** | **0.6562** | **0.6672** | **21/32** | **21/32** |

Needle per true class: simple **2/16**, detail **8/16**, gist **5/16**, both **4/16**. Scaffold: simple **16/16**, detail **9/16**, gist **9/16**, both **8/16**. Paired: Needle-only correct **8**, scaffold-only correct **31**, both correct **11**, both wrong **14**. This is not an independently adjudicated gold-label benchmark; route definitions admit subjectivity, and single-run accuracy is not causal generalization.

Native Needle returned valid tool-call proposals for **64/64**, but correctness was poor. Confidence AUROC vs author-label agreement **0.4772** (below 0.5); mean confidence on incorrect predictions **0.6861**, versus correct **0.6426**. **Do not** use raw Needle confidence for JEF authority, age gates or autonomous action. Needle per-row median latency **0.2469 s**, p95 **0.4749 s**, model peak RSS about **103.2 MB** on Ubuntu x86_64. Scaffold timings rounded to 0.0 seconds at 4 decimals; do not claim a Redmi speed result.

Original separate English96 native #850 was Needle **15/96** vs scaffold **46/96**. The new transfer64 was frozen before native execution, had **zero verbatim overlap** with English96, and contains equal English/German route strata. The poor native result persists in both languages, though the absolute rate differs by cohort.

## Interpretation and next independent package

The original C2 tool-calling head is **not suitable to replace the scaffold** on these labelled routes. Preserve original Needle model and exact source, and leave C2 authority unchanged. PR child `assistant/v13-run11-c2-bilingual-routehead-shadow-20261028` has preregistered a **separate** train64 set and fixed linear softmax head on frozen Needle embeddings; neither English96 nor transfer64 is allowed in training. Even a successful offline head would require new retention/resource/Redmi/human gates before activation.

No STEP2, B3 L1, Body-JEPA, LP3 heldout, JEPA weight, phone, whole-system or AGI promotion: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, `phone_measured=false`.
