# Core & Harness — native receiver token-row handoff

Date: 2026-11-22 (exact run start: UNKNOWN; checkpoint from GitHub PR metadata: 17:48:39 UTC)

## Ownership and checkpoint
- Lane: Core & Harness; no JEPA, Perception, or QA owner files changed.
- Parent: PR #2350, branch `core/v14-native-probe-model-byte-integrity-20261122`, head `266822c695b782fda16c2c7a26987fe6e76707fc`.
- Candidate: PR #2364, branch `core/v14-native-token-row-extraction-20261122`, exact head `2ef135185084acaca9c50c546c896af59f44138b`.
- PR #2364 is DRAFT / NOT_RELEASED and stacked on #2350. No force-push, no master edit, no model/weight/config change, no device action.

## Real code added
1. `native_latent_receiver --token-rows --model PATH --token-ids CSV` reads selected rows from the receiver model's input token embedding tensor (`llama_model::tok_embd`).
2. Row address uses checked `token_id * tensor->nb[1]`; row size comes from `ggml_row_size`; reads use `ggml_backend_tensor_get`; F32/F16/BF16/quantized rows are converted one row at a time through the pinned ggml conversion path.
3. Hard limits: 32 unique IDs, 262,144 returned float elements, dimension <=8192. Bounds, stride, shape, token range and finite output are checked. It does not call `llama_model_get_tok_embd()` or allocate/copy the full vocabulary embedding matrix.
4. Python `extract_token_rows` checks model bytes before and after, requires the pinned runner revision, model path under `home/models`, `local_confirmed=True` plus an interactive TTY, and validates source/type/shape/row identities. Model and tokenizer revision labels are caller-supplied and explicitly marked unverified by this low-level API. It grants no training authority or production route.
5. Native selftest now covers row-offset bounds and malformed/duplicate token IDs. Python fake-executable tests cover model hash changes, bad source/shape/IDs, full-table claims, symlinks, invalid revisions, explicit confirmation and non-TTY refusal.

## Research / provenance
- Pinned upstream: `ggml-org/llama.cpp` revision `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`; MIT license.
- Internal structure: [src/llama-model.h](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/src/llama-model.h) exposes `llama_model::tok_embd`.
- The full-table helper is in [src/llama-model.cpp](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/src/llama-model.cpp); this patch deliberately avoids it.
- Row read API: [ggml/include/ggml-backend.h](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/ggml/include/ggml-backend.h). Row sizing, tensor types and conversion traits are in [ggml/include/ggml.h](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/ggml/include/ggml.h).
- This is a pinned internal ABI, not a stable public llama.cpp API. A future update of llama.cpp must re-review the struct layout and tensor access before changing the pin.

## Tests and evidence
- `LOCAL_FULL_REPOSITORY=BLOCKED`: no checkout is present in the execution container; `git ls-remote https://github.com/RedMentos/Aii.git` failed because github.com DNS could not be resolved. No local compile or pytest pass for this PR is claimed.
- Parent #2350 exact head had six successful workflow checks when inspected; its model-byte/approval prerequisite remains separate.
- PR #2364 exact head at this handoff: native workflow run `45051475400` QUEUED; staged/integrated run `45051475305` QUEUED; push runs `45051469425` and `45051469468` QUEUED. These are not PASS evidence. Recheck latest head and every required job before review.
- Linux native model extraction against a real GGUF: NOT_RUN (no installed model was read).
- Android arm64: CI cross-compile is pending; no execution on Android.
- Redmi/Termux: REDMI_UNVERIFIED. No connected phone, private relay receipt, installation, model swap, or native row read was performed.

## User impact / deployment
- No current installed runtime behavior changes. PR #2364 is not a release and the binary is not auto-installed.
- No model was downloaded, switched, modified or trained. No private data, raw model rows or device data were published.
- B3 remains OFF/SYMBOLIC. This extractor is not trained latent coupling, a useful receiver effect, or an accepted B3 channel.

## Next executable steps
1. Recheck exact-head Actions for #2364; fix compile, Android cross-compile, Python 3.13/3.14 or staged regressions before review.
2. Obtain independent review of the internal tensor layout, dequantization, model path/TTY gate and bounded memory behavior. Keep the PR draft until this passes.
3. Coordinate with Perception owner PR #2346: its source-span alignment already pairs independent B1/B2 tokenizers. Do not edit their files. After the extractor is accepted, propose a separate adapter that uses receiver-tokenizer IDs plus these input rows as targets for a trainable B3 projector.
4. Any projector experiment must use source-disjoint train/holdout, same-source identity/symbolic/no-message/shuffled/zero controls, actual receiver causal utility, old-role retention, checkpoint/restart and rollback. No injection authority or production B3 promotion before those gates.
5. Boss/Integrator should port verified facts into `V14_WORK_BOARD.json`, `V14_RESEARCH_LEDGER.md` and `V14_USER_NEXT_ACTION.md` after cross-owner review; this lane did not edit the shared master documents.

## Current user decision
No action needed. No model download, swap, device command, permission change or experiment approval is being requested.
