# Native input-embedding receiver probe

This is a diagnostic, opt-in receiver executable for the staged V14 Runtime. It is not production B3, a trained cross-model adapter, KV-cache injection, or weight learning.

Upstream: ggml-org/llama.cpp at b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (MIT).

Build on Linux:
`cmake -S v13/code/v13/native/latent_receiver -B build-native -DLLAMA_CPP_DIR=/path/to/llama.cpp -DV14_LLAMA_REVISION=b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF`
`cmake --build build-native --target native_latent_receiver -j2`

The Android ARM64 CI workflow cross-compiles this executable and uploads a review-only artifact. It is not automatically installed by the runtime updater. The staged operator fails closed until a separately reviewed binary is installed at `$HOME/v13/bin/native_latent_receiver`.

The probe accepts source-bound B1/B2 tap vectors, uses llama_batch.embd -> llama_decode -> llama_get_embeddings_ith, and reports only dimensions, hashes, decode status, input-effect metrics and negative controls. Dimension mismatch is a hard refusal. Production routing, semantic-use proof and training authority remain false/zero.


## Read-only receiver token rows

The same pinned executable also supports:

    native_latent_receiver --token-rows --model PATH --token-ids 12,45,98

This reads only the requested rows from llama_model::tok_embd at the pinned
llama.cpp revision. It uses the pinned internal llama-model.h structure and
ggml_backend_tensor_get with checked token_id * tensor->nb[1] offsets. F32,
F16, BF16 and quantized rows are converted to float one row at a time. It
never calls llama_model_get_tok_embd() and never allocates the full vocabulary
matrix.

Limits: at most 32 unique token IDs, at most 262,144 output elements, embedding
dimension at most 8,192, checked tensor bounds and finite output. The Python
wrapper additionally verifies the installed model SHA-256 before and after
the read. Model and tokenizer revision labels are caller-supplied metadata;
the consuming Runtime must source them from its installed manifest.

This is an internal-ABI, read-only diagnostic, not a stable public llama.cpp
API, trained latent coupling, semantic-use proof, production B3 route, or
training authority. The existing model-byte and local-approval gates remain
separate. No model is downloaded, changed, or automatically installed.
