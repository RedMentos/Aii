# V14 native input-embedding receiver probe

This is an opt-in diagnostic bridge from a source-bound B1/B2 tap into a
separate native llama.cpp receiver context. It is deliberately **not** a
production B3 route, a trained cross-model adapter, KV-cache injection,
semantic-use proof, or a weight-learning path.

## Exact native API provenance

- Upstream: `ggml-org/llama.cpp`
- Pinned source revision: `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (b10964)
- License: MIT, verified from the upstream `LICENSE` at that revision
- Public C API used: `llama_model_n_embd_inp`, `llama_model_n_embd_out`,
  `llama_model_n_ctx_train`, `llama_batch_init` with `llama_batch.embd`,
  explicit `llama_batch.pos`, `llama_decode`, `llama_get_embeddings_ith`,
  and `llama_memory_clear`

The source tap is converted to little-endian float32 rows and carries the exact
sender checkpoint SHA, optional tokenizer revision, token IDs and explicit
zero-based contiguous position IDs from the whole-sequence tokenizer prefill.
The receiver validates row count, uniqueness, monotonicity and model-context
bounds, then uses those exact positions in llama_batch.pos. It checks its
native input dimension and refuses mismatches; no untrained resize or
synthetic projection is inserted.

The probe runs positive, zero, embedding-dimension-shuffle, reversed-row
(position-mismatch) and repeat controls in one receiver context, clearing
native memory between passes. For a one-row tap the row-order control is
explicitly marked not applicable. It reports sender/receiver checkpoint
provenance, position mode, decode status, dimensions, output norm,
positive-vs-zero RMS effect and separate control cosine values. An effect is
not semantic alignment.

## Runtime boundary

The only entry is the explicit operator command:

```text
:callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm
```

It uses the last completed user source, persists a source-bound tap receipt,
unloads the sender tap runner before loading the receiver model, and records a
`LatentReceiverPacket` with zero production and learning authority. The
normal chat path, channel policy, B3 level, model files, weights, permissions
and updater are unchanged. The receiver process is bounded to 64 rows, 8192
dimensions and at most two CPU threads; the operator must explicitly confirm
the model load. `--confirm` does not grant ongoing permission.

If the native executable is absent, the command fails closed. No model or
source download is performed by this code.

## Build

Use a pre-existing checkout of the exact upstream revision; this project does
not fetch source or weights:

```sh
cmake -S v13/code/native/latent_receiver -B build-native \
  -DLLAMA_CPP_DIR=/path/to/llama.cpp \
  -DV14_LLAMA_REVISION=b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-native --target native_latent_receiver -j1
cmake --install build-native --prefix "$HOME/v13"
```

The installed executable path is `$HOME/v13/bin/native_latent_receiver`.
The CI workflow builds the exact pinned API on Linux and cross-compiles
`arm64-v8a`; neither is a Redmi runtime test. The local self-test without
`V14_WITH_LLAMA` exercises only the bounded vector/control core, not a
native model. Redmi remains `REDMI_UNVERIFIED` until an authorized device
run returns a real native receipt.
