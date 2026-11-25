# Research & Perception Run 17 — native input-embedding row contract

Date: 2026-11-25
Role: Research & Perception
Whole-Canon link: https://github.com/RedMentos/Aii/issues/1984
Core receiver: https://github.com/RedMentos/Aii/pull/2499
Research branch PR: https://github.com/RedMentos/Aii/pull/2502

## Code checkpoint

- Branch: `research-perception/v14-token-span-manifest-integrity-20261125-run16`
- Exact current head: `2f74fa94d2ad4d0004ec61ea128bdec4d320e569`
- Added `v13/code/v13/native_input_embedding_tap.py` (blob `b92d2f635fcd3efcc18c2dcc2785aa192002c815`).
- Added `v13/code/tests/test_native_input_embedding_tap.py` (blob `ed4c039b6871efa62926707ea920d1ff65f18ebc`).
- Extended `.github/workflows/v14-latent-token-alignment.yml` (blob `79a9342e0b2b495593eb982e8e0c409fdab02448`).
- The manifest accepts only role-derived `b1/b2/c3.input-embedding.v1` tap IDs and binds exact UTF-8 byte-piece token IDs/spans, source ID/hash, event, brain generation, model/tokenizer revisions, embedding dimension and per-row SHA-256. It rejects final-RMSNorm IDs and changed source/rows.
- This is the Perception-side data contract for a future native row extractor. It does not extract native rows, change `LlamaRunner.tap`/`Cognition.tap`, inject a receiver, train weights, or enable production B3.

## Tests

- Adapter workflow RUN 45648811640: 53/53 PASS on Python 3.13 and 3.14; exact py_compile PASS; public privacy scan CLEAN.
- Runtime-deployment integrity RUN 45648811730: PASS on Python 3.11 and 3.14.
- Staged/integrated regression RUN 45648811577: IN_PROGRESS at the last poll.
- Full local Aii checkout/pytest: BLOCKED / NOT_RUN (no local checkout mounted; local GitHub DNS unavailable).
- No native GGUF, native receiver, Android arm64 build or Redmi test was run.

## Research R-148 — exact upstream row-select API

- Current Core PR #2499 pins llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`; that exact pin has only `llama_model_get_tok_embd` for the full F32 token-embedding matrix, not a row-select API.
- Upstream llama.cpp commit `a8fad21e9949c20f6b21692c8d38a8aba422eafe` (2026-11-09, MIT) contains `llama_model_get_tok_embd_rows(model, tokens, n_tokens, out)` in `src/llama-ext.h`. Its implementation in `src/llama-model.cpp` calls `llama_tensor_rows_to_f32` for each requested token row.
- `llama-ext.h` explicitly labels itself staging/WIP. Any use requires a reviewed exact pin, inclusion path, Linux native build/selftest and Android arm64 cross-compile; do not assume stable ABI.
- Calculated output geometry: 64×1024×4 = 256 KiB; 64×2048×4 = 512 KiB. These are output-buffer sizes only, not measured process RSS or peak backend memory.
- Sources: https://github.com/ggml-org/llama.cpp/blob/a8fad21e9949c20f6b21692c8d38a8aba422eafe/src/llama-ext.h ; https://github.com/ggml-org/llama.cpp/blob/a8fad21e9949c20f6b21692c8d38a8aba422eafe/src/llama-model.cpp ; https://github.com/ggml-org/llama.cpp/blob/a8fad21e9949c20f6b21692c8d38a8aba422eafe/LICENSE .

## Integration handoff

Core should review a compatible llama.cpp pin update, include the exact staging header, extract only no-special content-token rows, call the new manifest builder and persist the result with SourceRef/event/generation/blob bindings. Keep final-RMSNorm sender taps, receiver input-embedding taps and event-pooled `LATENT_PREFIX_V1` distinct. Then form a source-disjoint native pair cohort and run same-model parity, exact-text, no-message, zero, shuffle, repeat and OOD controls, followed by receiver-task utility, gradients/parameter diff, old-task retention, restart and rollback. No B3 activation before independent review.

## Device / release boundary

Latest available consented private V13OBS #115 metadata remains historical (2026-11-24 09:28 UTC): auto-update enabled and installed SHA `8d93236c753f0194224c19edc7411d8d7082b1d6`, but AI runtime STOPPED_BY_USER, autostart false and model process stopped. No newer authenticated device receipt was available in this run. No device command, update request, restart, model/weight change or permission change was performed. PR #2502 is OPEN/DRAFT and NOT_RELEASED; GitHub push is not deployment. REDMI_UNVERIFIED; production B3 OFF.


## Final CI and branch readback correction

The exact code/test head `2f74fa94d2ad4d0004ec61ea128bdec4d320e569` is fully CI-green: adapter 53/53 PASS on Python 3.13/3.14; runtime-deployment integrity PASS on Python 3.11/3.14; staged/integrated regression PASS (integrated 424 passed, 3 skipped, 58 subtests; staged 255 passed, 10 skipped, 47 subtests). The later docs-only commit `8f057c3d83d88bb5eadfc6a6629b3afce1b81e3d` is read back on the branch ref, but PR #2502 API still showed the old head `2f74fa94...` at last poll. Do not claim PR synchronization until verified.
