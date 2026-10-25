# Run328 checkpoint — source-only tensor-delta auditor verified, native bytes pending

UTC 2026-10-25. Preregistration `a1abb60716caa99c65bd19882d692a1a1084498e` before implementation. Source head `467f25991651de3edc8cdd523df21e4fe497856d`, PR325, parent Run327/PR324 (not main). New read-only `scripts/audit_native_weight_delta_run328.py` + `tests/test_native_weight_delta_run328.py` + dedicated CPU CI, no original runtime/evaluator/trainer/Canon/model/seed/cohort change.

## Actual verified evidence

GitHub Actions `40215083602`, job `121234370822` **SUCCESS**; 13/13 synthetic adversarial source-only tests PASS, exact original source hashes and Canon unchanged, privacy CLEAN. Raw artifact `12607098114`, ZIP SHA256 `a49a0216c10f2bce681b350e35d65ebceb7a288143ed1718fc7748c64ea1ad4b` (30-day retention). Test categories: exact checkpoint SHA/epoch binding, missing source/selected tensor, shape/type/size drift, changed nonselected tensor, no epoch1/epoch2 update, nonfinite selected tensor, bitwise-only without numerical delta, negative gates.

## Scope and open gates

**No native GGUF tensor audit executed**; the 13 software tests are not optimizer evidence. The verifier is ready to compare full original Run324 FP32 master with two real Run319 epoch checkpoints and original Run320 report **after** the original Run327 native job completes. It will check 148 tensor payload SHA, exactly 4 FFN trainable tensor names, unchanged 144 other tensor payloads, numerical finite update in each epoch, and independent Run321 exact raw-score audit. Failure stays RED, no weights/GGUF published.

Run327 active original experiment: `40214796252`, source head `0c969d97b6ffad0f0be1022de684752cc8056fc1`. Original Run325 `40213614735` RED before optimizer preserved. Original Run326 `40214511020` PASS metadata-only path drift; no optimizer. Current gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE.

## Owner and exact next command

Owner Run328 source-only complete; native integration **not yet authorized to claim** and requires separate preregistration/serialized model job. Next: inspect `gh run view 40214796252 --repo RedMentos/Aii`, download Run327 closed raw artifact and check actual native optimizer/selection/Run321 audit. If Run327 succeeds, prepare separate native GGUF tensor audit without overwriting or silently retuning original 8/6/5/12 cohort; otherwise preserve failure and continue an independent canonical package. No private Drive upload (previous anyone-writable destination rejected).
