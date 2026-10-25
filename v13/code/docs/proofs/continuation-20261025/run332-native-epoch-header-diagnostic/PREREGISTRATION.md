# Run332 preregistration — diagnose Run330 native GGUF metadata without changing optimizer

UTC 2026-10-25. Parent verified remote `1f9b00f49bdab2689508f94925d167b5cde13071` / PR328. Own review branch `assistant/run332-native-epoch-header-diagnostic-20261025`; do not modify Run330 evaluator, Run319/329 trainer, original Run328 auditor, frozen Run320 cohort, model/source SHA, seed, loss, thresholds, Canon, age or approval.

## Observed RED and scope

Run330 exact-head `c847c4244ccb34f950e5be05acaa8078dfbbde49`, GitHub Actions run `40215965854` (job `121237031858`) completed **FAILURE** only at enforced independent Run328 audit. Logs independently inspected on 2026-10-25: official pinned source, dependencies, C++ build, exact FP32 master `5d200c19...`, native two-epoch optimizer/evaluator and independent Run321 raw-score JSON audit each exit 0. Native evaluator reports `COMPLETE_NATIVE_EVALUATION` and `native_training_executed=true`; epoch1 meets **diagnostic-only** thresholds (facts 2, paraphrases 1, near-miss 0, no forgetting), epoch2 fails retention (one baseline probe forgotten). Run328 auditor exits 2: `ValueError: not original lfm2 ALL_F32 GGUF`. This is not a verified tensor-delta PASS. Original raw artifact ID `12607866770`, GitHub-upload reported ZIP digest `5d306a9de79f231363b0d03e2197ce057c146513511094186fdebf2360b75fd1`; independent download/hash still pending. No weights in artifact.

## Hypothesis and fixed test

Likely one or both `llama_model_save_to_file` epoch checkpoints differ in `general.architecture` or `general.file_type` metadata despite the original master and tensor payloads being F32. **Do not assume which field or change the auditor based on a guess.** Create read-only header diagnostic with pinned b10964 GGUFReader. Report for master/epoch1/epoch2 only: field presence/type/value, tensor inventory/count/type histogram, selected name presence, total F32 element count, and full-file SHA256/size. Do not emit weights, tensor payloads, tokenizer text, prompts, private data or model files. Check actual report receipt SHA, immutable original master hash, and fail closed on missing files or non-F32 tensors. Add adversarial synthetic parser tests for absent/malformed architecture/file_type, mixed F16, missing selected tensors, duplicates and mismatched receipts. **No relaxation of Run328 until actual metadata differences are observed.**

Run separately serialized Linux-native CI reusing **exact unchanged** Run330 train/eval recipe and Run321/328 audits; append diagnostic after original Run328 result. Keep Run330 failure evidence, full raw/hashes, privacy and negative gates. If a metadata-only discrepancy is verified and all tensors remain F32, preregister a separate minimal independent auditor compatibility patch and rerun, never silently change a frozen original. No AG6/Body-JEPA/STEP2/B3/Redmi/V13 promotion. No production merge or public weights.

## Next

Implement diagnostic source/tests and isolated workflow, run exact-head CI, inspect raw, verify remote bytes, then select the next independent package. All negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE.
