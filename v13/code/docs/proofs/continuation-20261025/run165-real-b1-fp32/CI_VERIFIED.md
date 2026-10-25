# Run165 Linux CI real pinned B1 FP32 export VERIFIED (2026-10-25)

Exact head `bac5cd7a7c4850a5f53259546cdc3a7e4cb04c49`, GitHub Actions `40164133666`, job `121081978291`, **SUCCESS**. Registered revision/license/size/SHA assertions PASS. Exact public B1 GGUF downloaded privately; 695755488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1` independently reverified in this run. Run160 parser reports 148 descriptors and 55 F32; preregistered sorted first four eligible 1D F32 vectors exported by Run162 to private NPZ, and Run163 external-SHA-bound byte-exact source/manifest/NPZ audit PASS. Log: `RUN165_REAL_B1_FP32_EXTRACT_AUDIT_PASS 4 AUTHORITY 0`. Official privacy `c1f124d9d..HEAD: CLEAN`.

Metadata-only GitHub Actions artifact ID `12587178813`, ZIP SHA256 `5066f297df054dd7683730d01226ab01beb5a504ed417ad37a180b1c94202d57`, 1258 bytes. Weight/model/NPZ bytes were never uploaded; model and private master removed by EXIT trap. Exact selected tensor names/hashes live in metadata-only artifact, not invented here.

**Evidence grade:** Linux CI real pinned source file integrity + FP32 inference slice export/roundtrip + independent byte-level audit, **not** native model inference, trainable master lifecycle, gradient, EMA, requantization, retention, answer utility, Body-JEPA or Redmi. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. No gate promotion.

Next: inspect the metadata-only artifact independently and verify source hashes; prepare separately registered train-master lifecycle/gradient/EMA/requantization test with actual weights and negative controls, but do not inject changes into inference model or bypass approval. Run164 full suite still FAIL and is a separate open blocker.
