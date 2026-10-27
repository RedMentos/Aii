# LP3 LR × frozen-prompt normalization — Linux-native result (2026-10-27)

**Review-only child of PR #770**, parent `73f1ceac47804bfcf7a00e9555e7ab7d0d4b8b83`, not main. Prereg commit `f9e890687106e20ea4768933d5a8f19917a04988` preceded implementation and execution. Frozen original trajectory blob `488cd12de3d5103e2a456f42148697fd15d66bc6` unchanged. New source blob `851f4b14f31004c838053d971bf800199bbd5546`; original six-row cohort, seed109, 24 steps, FP32 master `LiquidAI/LFM2.5-350M` revision `120bf032c36dd1273de754669da040dba7ad4982`, full SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`.

**Actions 40579301037 SUCCESS:** 30/30 focused tests PASS; FROZEN, PREREG, INSTALL, UNIT, DOWNLOAD, VERIFY, NATIVE, COMPILE, PRIVACY, DIFF all exit 0; privacy CLEAN. Original raw ZIP artifact `12769221227`, SHA256 `3d5b5287975cf953b4ea650256f478b81a4a1ccabb23292e7011aceae77ad47d`; CRC verified; HEAD `2a5a63c06d45f2bacb74fb491ccd28b967f6c682`; `RESULT.json` SHA256 `d4452c3c581559ea02a5b412426908887c66c8bd1790d110eb2916ad6cee42a8`. Private native Library backup `/V13-Checkpoints/2026-10-27/Automation11ZO-LP3-LR-Norm/NATIVE_40579301037.zip` uploaded and re-materialized byte-identical SHA256.

Four arms (all 24 steps completed, same initial trainable SHA `f422575d1b01c6446852e9f9539082a2b097dd5bab00aec4f70184179505a033`):

| Frozen prompt feature | AdamW LR | Predictor positive-gradient steps | First zero-gradient | Mean tanh saturation | Train CE step0→step23 |
|---|---:|---:|---|---:|---:|
| raw | .005 | 18/24 | step8 | .957723 | 10.88436→9.79083 |
| raw | .0005 | 24/24 | none | .398031 | 10.88436→4.03670 |
| per-row LayerNorm | .005 | 24/24 | none | .900920 | 10.86377→9.18861 |
| per-row LayerNorm | .0005 | 24/24 | none | .000814 | 10.86377→8.18816 |

**Interpretation:** The 10× lower learning rate eliminated exact zero predictor gradients over these 24 steps and reduced saturation substantially even without normalization; LayerNorm plus low LR nearly eliminated saturation. Normalization at high LR retained high saturation despite nonzero gradients. Train CE on the fixed six facts is **not** heldout answer quality, retention, JEPA utility or a reason to enable weight learning. No answer/retention scoring occurred. All original LP1/LP2/BJ1/STEP2/B3 negative gates, jepa_weight0 and Age authority0 remain.

**Cross-host caution:** Compared to original PR #770 raw NO_EVAL receipt (artifact `12768346420`, SHA256 `1982e326a9ff9cba87200b2f3afb30125163d29d92041e131e0bbae805ec16da`), the raw .005 arm has the same initial trainable SHA, frozen-base sample SHA, and first zero-gradient step8, but slightly different FP32 step0 metrics and a different final trainable SHA across separate Linux runners. Do not claim byte-exact cross-host trajectory replication or deterministic generalization. Within this run all arms share the same initialized weights and source/model/seed.

**Next:** separately preregister and measure heldout answer CE/top1 with correct-state vs wrong-source/zero-prefix and retention for **all four arms**, plus new disjoint phrasing controls; then repeat on independent host if necessary. Keep original failed PR #734 and all prior negative evidence unchanged. Full source-wide software regression has its own workflow; status must be recorded separately from native proof.

Exact native command: `cd v13/code && PYTHONPATH=. python scripts/lp3_lr_norm_ablation.py --master <verified-pinned-master> --out <new-exclusive-receipt.json> --execute-native`. Independent review required; no auto-merge, no production integration, no Redmi/thermal/energy proof. V13 incomplete.

**Full source-wide Actions 40580134684 SUCCESS:** 1922 tests OK (1 skipped), INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN, original ZIP artifact `12769976261` SHA256 `b38dd64a32e37ca8d9622d2463fe6c808716f020f2f15a5c2ca5ad04fa3243a1`. HEAD `ed1f999be5107d646514946c190edb98cffe2954`, source blob `851f4b14f31004c838053d971bf800199bbd5546` verified, CRC clean; private Library `FULL_40580134684.zip` re-materialized byte-identical. This does not extend native evidence to Redmi or prove answer utility.
