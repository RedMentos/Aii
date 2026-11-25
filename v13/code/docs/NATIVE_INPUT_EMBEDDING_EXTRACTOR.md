# V14 native input-embedding extractor

## Purpose

native_input_embedding_extractor is a read-only native producer for the
receiver model's **input token-embedding table rows**. It uses the pinned
llama_model_get_tok_embd_rows API from src/llama-ext.h at llama.cpp
revision 2851b3bcbf8d993a2243ae751c0a7dfa8e944a40.

It is deliberately distinct from the existing final-RMSNorm prefill tap:
these are static input-table rows, not hidden states, KV-cache contents,
attention outputs, or final-layer activations.

## Contract

The caller must:

1. Obtain ordered token IDs and token pieces from the same native tokenizer
   request, with add_special=false and pieces enabled.
2. Resolve an already-installed receiver GGUF and its exact ModelRegistry
   revision/hash. No model download or model swap is performed.
3. Hash the installed GGUF and extractor binary independently.
4. Call the binary with those hashes and the exact ordered token IDs.
5. Validate the receipt and rows, then pass them to
   native_input_embedding_tap.build_native_input_embedding_tap_manifest
   from the Perception-owned contract.

The native binary validates all token IDs before calling the row API. This is
important because the upstream implementation returns zero on an invalid ID
and may have already copied earlier rows. The wrapper rejects incomplete
element counts, non-finite/oversized values, zero rows, source-tensor geometry
mismatches, model/hash drift, token-order drift, and binary/model changes
during the call.

The receipt is a provenance envelope, **not a cryptographic signature**.
The Python caller hashes the actual files before execution, passes those
hashes into the native process, and rechecks file identity/metadata afterward
to detect replacement or mutation without reading a multi-gigabyte GGUF twice. The binary receives only the model path, revision/hash, extractor
hash, and token IDs; it receives no source text.

## Bounds and privacy

- 2–64 ordered token IDs, no more than 8192 embedding dimensions, and at most
  524288 F32 elements.
- CPU-only model load (n_gpu_layers=0); one model at a time.
- No tokenization, generation, training, persistence, network, or device
  control in the native executable.
- The Python wrapper requires an explicit idle-guard callback before the
  native process starts; the Runtime caller must confirm no active turn and
  release the native model pool first. It uses argv (never a shell), bounded
  execution time, no-follow regular-file hashing, file identity checks, and no
  raw stderr in exceptions.
- The returned vectors are ephemeral. This component does not write them to
  SQLite, a file, a checkpoint, or the public repository.
- The API is explicitly STAGING_WIP; the extractor is not a production B3
  latent channel and does not prove learned cross-organ coupling.

## Build and evidence

CMake consumes an external llama.cpp checkout at the exact pinned revision.
The upstream source is MIT-licensed; the CI job verifies its LICENSE, builds
the Linux executable, runs parser/row-contract selftests, and cross-compiles
an Android arm64-v8a artifact. The Android artifact is review-only and is not
installed on the Redmi.

A Linux build or Android cross-compile is not a real GGUF row-read measurement.
Until the executable is run against an already-installed model on the Redmi
with a private, consented receipt, device status remains REDMI_UNVERIFIED.
