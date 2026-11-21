# Research/Perception handoff — native hidden-state ingress candidate (2026-11-21)

## Functional artifact

`v13/code/v13/ggml_extractor_ingress.py` consumes one bounded float32 activation row from the exact NPY shape emitted by `ggml-extractor` 0.2.0 (`frames, requests, n_embd`). It streams the file hash, validates the metadata sidecar, reads only the selected row, rejects nonfinite/unbounded values, and passes numeric values into the existing `latent_bridge.Projector` and `receive` ports. It never stores prompt text, never updates weights, and never grants training/action authority. The receive result is always `SHADOW_UNVERIFIED`.

This is an ingress/consumer adapter, **not** the native capture itself, not proof of cross-model training, not KV-cache injection, and not Android integration. Metadata is caller-supplied and cannot attest that the NPY was actually produced by the named extractor. A real native receipt is still required.

## Upstream reuse and licensing

- Upstream: https://github.com/gdonninelli/ggml-extractor
- Reviewed revision: `0449f6335ce99f009c204e8c844a78eca6e9289d`, version `0.2.0` (main commit dated 2026-09-11).
- License: MIT (`LICENSE` at the reviewed repository revision). No upstream source, model weights, or dependency was copied into Aii.
- Upstream README says it captures selected `l_out-<layer>` tensor rows through llama.cpp `cb_eval`, returns `(n_frames, n_requests, n_embd)` float32 C-order `HiddenStates`, and can share the same model/context/KV cache with ordinary inference. It also warns that internal tensor names are unstable and may change with llama.cpp graph rewrites.
- Upstream README reports verification against llama.cpp `5ecbe1ac17ec0484c5b44af0bd580cdc9c428ed4` and advertises macOS/Linux, not Android.
- The Aii runner registry currently pins llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (tag `b10964`, 2026-09-14). This is a different revision; compatibility is therefore marked `UNVERIFIED`. Even the upstream-reported revision is explicitly labelled Linux/macOS-only by this adapter, never Android-verified.

## Why this is useful

The existing `latent_bridge.Projector` transports numeric vectors, but the mainline tree has no proven source for real B1/B2/C3 hidden-state vectors. The extractor is a concrete candidate for capturing internal layer outputs without loading a second model/context. This adapter supplies a bounded, source/model/layer/token-bound path from its NPY output into the existing numeric projector/receiver interface.

## Required next native proof

1. Build the exact pinned extractor against the Aii llama.cpp revision and the actual LFM2.5 GGUF runner; do not assume the README's older revision is ABI-compatible.
2. Verify tensor names, widths, selected token rows, and capture correctness on each actual model role (B1, B2, C3). Record the model revision and file SHA, llama.cpp commit, extractor commit, native architecture, compiler, and ABI.
3. Compare armed/unarmed logits bit-for-bit and measure capture overhead, RSS/PSS, prompt prefill and decode latency; the extractor README's CPU timing is not Redmi evidence.
4. Implement receiver-side input embedding injection only after checking the target model's exact input width/architecture. `llama_batch.embd`/custom decode path is a separate unproven integration step; a projected vector is not automatically a valid receiver prompt.
5. Run source-disjoint projector learning with holdout, negative controls, before/after parameter diffs, retention, checkpoint/restart and rollback. No private prompt/activation training without explicit local consent.
6. Android NDK/Termux ARM64 build and actual Redmi runtime test remain required; no model download or swap is requested by this handoff.

## Local test evidence

The Python adapter is tested against locally generated NPY fixtures that follow the documented upstream layout. This validates parser, provenance, bounds and numeric receiver wiring only. It does not execute `ggml-extractor`, llama.cpp, a GGUF model, native hidden-state capture, Android, or weight learning.
