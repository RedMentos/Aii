# Native input-embedding receiver probe

This is a diagnostic, opt-in receiver executable for the staged V14 Runtime. It is not production B3, a trained cross-model adapter, KV-cache injection, or weight learning.

Upstream: ggml-org/llama.cpp at b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (MIT).

Build on Linux:
`cmake -S v13/code/v13/native/latent_receiver -B build-native -DLLAMA_CPP_DIR=/path/to/llama.cpp -DV14_LLAMA_REVISION=b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF`
`cmake --build build-native --target native_latent_receiver -j2`

The Android ARM64 CI workflow cross-compiles this executable and uploads a review-only artifact. It is not automatically installed by the runtime updater. The staged operator fails closed until a separately reviewed binary is installed at `$HOME/v13/bin/native_latent_receiver`.

The probe accepts source-bound B1/B2 tap vectors, uses `llama_batch.embd -> llama_decode -> llama_get_embeddings_ith`, and also reads the receiver’s last-position logits with `llama_get_logits_ith`. Protocol `/4` supports two deliberately separate input contracts: `ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL` for token-aligned rows, and `LATENT_PREFIX_V1` for exactly one event-pooled vector at virtual position zero in a fresh receiver context. The prefix mode carries no token IDs or tokenizer revision and is never represented as a one-row tokenizer prefill. It reports receiver vocabulary size, greedy next-token IDs and margins for positive, zero, shuffled and repeat controls; row-shuffle is explicitly not applicable to the one-row prefix. These are native input-consumption and next-token-distribution measurements only; they do not prove semantic utility, trained cross-model alignment or production B3. Dimension mismatch is a hard refusal. Production routing, semantic-use proof and training authority remain false/zero.


`LATENT_PREFIX_V1` is accepted only for an event-pooled adapter candidate whose receiver tap is the exact receiver `*.input-embedding.v1` space. The Runtime binds the adapter file hash/identity, both installed model revisions and hashes, the current source/event/generation, and the sender tap. The prefix vector is diagnostic-only: no production B3 route, no semantic-use proof, no training authority and no weight changes. A receiver-side task-utility experiment with exact/no-message/zero/shuffle/repeat/parity/OOD controls is still required before any production B3 decision.


For an explicitly approved diagnostic, place the adapter checkpoint under `$HOME/v13/data/latent_adapters/<adapter-name>` and run:

```text
:callosum arm-probe B2_GIST C3_LANGUAGE --latent-prefix <adapter-name> --last-source --confirm
:callosum native-probe B2_GIST C3_LANGUAGE --latent-prefix <adapter-name> --last-source --confirm
```

The adapter must be fitted to the receiver's exact `*.input-embedding.v1` tap and current model revision/hash. The existing B1/B2 final-RMSNorm tap-pair fitter does not by itself create a C3 input-embedding adapter; those candidates are deliberately rejected. No command here creates or downloads an adapter, and no adapter is promoted to a production route.
