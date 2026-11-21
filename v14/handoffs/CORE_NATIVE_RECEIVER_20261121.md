# Core & Harness — native input-embedding receiver checkpoint (2026-11-21)

## Ownership and branch

- Owner: Core & Harness
- Base: gpt6/v13-private-remote-bridge-20261111 at bdcad466ffea75a2b41f7d23be168f53c7197d20
- Branch: core/v14-native-latent-receiver-20261121
- Code checkpoint at this handoff: 0342be28d8998c560024688657533ce844937301
- PR: pending creation; no merge or release claimed

## What is now connected

1. Cognition.native_receive takes a source-bound B1/B2 LatentTapPacket, validates its stored feature file, unloads the sender tap runner, then invokes a separate native receiver process for the selected installed B1/B2/C3 model.
2. :callosum native-probe <sender> <receiver> --last-source --confirm is the only entry. It explicitly selects the last completed source and requires a one-shot confirmation. It does not run on normal chat turns.
3. The C++ receiver uses the pinned llama.cpp C API llama_batch.embd → llama_decode → llama_get_embeddings_ith. It queries llama_model_n_embd_inp/out and refuses dimension mismatch rather than inserting an untrained resize.
4. It runs positive, zero, shuffled and repeat controls; records decode status, dimensions, output norm, input-effect RMS and control cosine values. Only summary metrics and hashes are persisted; no prompt text or raw receiver output is returned.
5. LatentReceiverPacket has a strict contract: production_route=false, semantic_use_proven=false, training_authority=0, native_receiver_authority=0. :callosum status can display the latest probe without promoting B3.

## Provenance and licensing

- Upstream ggml-org/llama.cpp, exact revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (b10964).
- The exact pinned include/llama.h was fetched and checked for llama_batch.embd, llama_batch_init, llama_decode, input/output embedding dimensions, llama_get_embeddings_ith and llama_memory_clear.
- The upstream LICENSE at that revision declares MIT. No upstream source or model weights are vendored or downloaded by this patch.

## Verification

### LOCAL_LINUX — executed here

- Python wrapper isolated suite: 6 passed. It covers pinned revision, model-path/hash binding, malformed vectors, dimension mismatch, no-effect versus effect, timeout and subprocess cancellation. This was run in an isolated temporary package, not a full Aii checkout.
- C++ core-only compile: c++ -std=c++17 -Wall -Wextra -Werror — PASS; --selftest — PASS.
- C++ adapter syntax compile against a local declaration stub matching the inspected pinned API signatures: PASS. This is not the real llama.cpp header or linked library.
- Python py_compile for the isolated wrapper: PASS.
- Full repository LOCAL_LINUX tests: BLOCKED — no full Aii checkout is mounted and GitHub DNS resolution is unavailable in this environment.

### CI / native

- Exact pinned llama.cpp Linux build and Android arm64-v8a cross-compile workflow added: .github/workflows/v14-native-latent-receiver.yml.
- Exact-head PR CI: PENDING (no PR run available at handoff creation).
- Native model execution: NOT RUN — no installed native receiver binary/model pair was loaded in this environment.
- Redmi/Termux: REDMI_UNVERIFIED — no authorized connected phone receipt exists.

## Limits and risks

- This is native input-embedding ingress, not K/V-cache injection and not a trained cross-model adapter.
- It is a separate receiver context/process, not the production llama-server context. The sender runner is unloaded first to avoid intentionally holding both model copies simultaneously.
- Dimension mismatch is a hard refusal; there is no untrained projection or silent truncation.
- A successful decode plus nonzero input-effect RMS proves only that the receiver computation changed under the supplied vector versus the zero control. It does not prove semantic use, useful offers, model-to-model alignment, or better task performance.
- The normal callosum policy still keeps LATENT unavailable in production. No weight, model, Age, X10, permission, updater or user-data state was changed.
- The executable is not part of the installed app yet. The updater/deployment path has not been changed; this branch is NOT_RELEASED.

## Next executable actions

1. Open the draft PR and run exact-head Python 3.13/3.14 regressions, pinned llama.cpp Linux link/build and Android ARM64 cross-compile. Fix compile/test failures on this branch.
2. After review, have Boss integrate the code and handoff without overwriting the active #2258 composition.
3. Only after a signed/reviewed build is packaged through the existing release path, request an explicit one-shot Redmi native probe. First compare actual tap output dimension with receiver n_embd_inp; record a real receipt or a dimension-mismatch receipt. Do not change production routing.
4. If the native pair consumes the input, continue with source-exact/no-message/symbolic/shuffled/OOD/receiver-task controls and a measured trainable model-specific projection. Production B3 remains OFF until a trained alignment improves held-out receiver utility and survives retention/restart/rollback.
