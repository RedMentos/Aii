# Run162 preregistered FP32 inference-slice export candidate

Base `0858a8b5e8a97a7e21ae7df1a63ada55e7a7dbfe` (Run161 full-model preflight branch, still pending). Owner Run162: limited layout extension to Run160 read-only GGUF parser, new FP32 exporter, tests, CI and proof. No edits to frozen `v13/body_training.py`, Runtime, registered models, weights, native runner or V13 Canon.

Goal: from a **full-file SHA-256 verified** GGUF, extract at most 8 selected 1D F32 inference tensors (<=16MiB each) into a separate private FP32 NPZ candidate; verify exact float32 roundtrip and unchanged source file. Reject quantized/nonvector/missing/out-of-file/nonfinite slices, wrong SHA and existing destination. Do not publish model or exported weight bytes.

Local synthetic tests (10/10 PASS) were exploratory before this protocol; they are not native or preregistered model results. CI will independently test the exact source. Actual B1 model extraction must wait until Run161's full-file SHA proof is verified; no concurrent heavy model jobs.

This candidate is **not body training**: no gradients, EMA, requantizer, active expert, runtime injection, utility or retention. Train master and Body-JEPA authority stay 0; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE.
