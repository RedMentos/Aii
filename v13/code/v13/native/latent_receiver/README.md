# Native input-embedding receiver probe

This is a diagnostic, opt-in receiver executable for the staged V14 Runtime. It is not production B3, a trained cross-model adapter, KV-cache injection, or weight learning.

Upstream: ggml-org/llama.cpp at b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (MIT).

Build on Linux:
`cmake -S v13/code/v13/native/latent_receiver -B build-native -DLLAMA_CPP_DIR=/path/to/llama.cpp -DV14_LLAMA_REVISION=b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF`
`cmake --build build-native --target native_latent_receiver -j2`

The Android ARM64 CI workflow cross-compiles this executable and uploads a review-only artifact. It is not automatically installed by the runtime updater. The staged operator fails closed until a separately reviewed binary is installed at `$HOME/v13/bin/native_latent_receiver`.

Reviewed artifact provenance: workflow run `45094188446`, source commit `0a470ada486b848f3ab5762ba1074e7660803eee`, artifact ID `14782878162`. The ZIP SHA-256 is `b59e2bbc1e57e4b0d816e9709324ec39a7ede0b9a61d9f20a7464f0e8ab23d99`; the contained Android ARM64 executable SHA-256 is `b82aba4da4aac24bef1012fbbcf89735016f7cf5297766adfbb5ffa7f8daf704`. The runtime accepts only that reviewed executable hash. It opens the executable with `O_NOFOLLOW|O_NONBLOCK` relative to the held `home/bin` directory, verifies the descriptor, and executes `/proc/self/fd/N` with `pass_fds`; it does not execute a replaceable pathname. Test-only injected executables are also descriptor-pinned but do not inherit the production artifact hash.

The probe accepts source-bound B1/B2 tap vectors, uses llama_batch.embd -> llama_decode -> llama_get_embeddings_ith, and reports only dimensions, hashes, decode status, input-effect metrics and negative controls. Dimension mismatch is a hard refusal. Production routing, semantic-use proof and training authority remain false/zero.
