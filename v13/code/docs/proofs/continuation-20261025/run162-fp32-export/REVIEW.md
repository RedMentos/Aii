# Run162 independent FP32 slice export review

From a full SHA-256 verified GGUF only, select up to eight one-dimensional F32 inference tensors, each <=16MiB. Compute GGUF tensor-data alignment/offset from bounded metadata, validate every slice lies inside the model file, reject quantized/nonvector/nonfinite tensors, write a separate private NPZ with exclusive create, read back exact float32 values, and verify source model bytes remain unchanged.

Local synthetic tests **10/10 PASS**; inherited Run160 parser tests to be checked on full GitHub CI. No real model weights were available locally; Run161's full-model SHA preflight is a prerequisite. The candidate does **not** implement gradients, EMA, requantization, native training, online integration or retention. Master/training authority 0, all V13 gates negative. Do not publish exported weights.

Source hash verification against remote Git blobs required; any failed CI attempt must be retained. Next: exact-head CI and then, only after Run161 verified, a serialized real B1 read-only FP32 slice export.
