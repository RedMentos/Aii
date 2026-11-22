# Core & Harness — native receiver staged-runtime checkpoint (2026-11-22)

## Ownership and exact base

- Owner: Core & Harness
- Integration base: `boss/v14-recall-store-pin-rebind-20261122` at `91227b171f3e6c2251767f20cd494f34d6ec24fa`
- Working branch: `core/v14-native-receiver-stage-20261122`
- This current-base candidate replaces the old-base-only #2266 path; #2266 remains open until this candidate passes.

## What is connected in the staged Runtime

- A source-pinned overlay is applied after the Boss base → fair B1/B2 scheduling → audio-context → C4 receipt composition. It does not edit frozen source modules or the QA-owned Record-Only guard.
- The overlay adds `Cognition.native_receive` and an explicit `:callosum native-probe <sender> <receiver> --last-source --confirm` operator route.
- The tap is source-bound to the last completed event. The sender tap runner is unloaded before the separate receiver process loads the installed receiver model.
- `LatentReceiverPacket` records hashes, roles, dimensions, positions, decode status and input-effect/control metrics. `:callosum status` validates and displays the bounded receipt without exposing prompt or activation values.
- Production routing, semantic-use claims, training authority and receiver authority remain hard false/zero. Normal chat routing is unchanged.

## Native provenance

- Upstream `ggml-org/llama.cpp` pinned commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (b10964), MIT.
- Uses `llama_batch.embd`, `llama_batch_init`, `llama_decode`, `llama_get_embeddings_ith` and `llama_memory_clear`.
- No model weights or upstream source are vendored. Dimension mismatch fails closed; no untrained resize, K/V injection, trained projection or production B3 promotion.

## Verification boundary

- Exact-head Python 3.13/3.14 staged Runtime tests, pinned Linux build and Android ARM64 cross-compile are pending CI.
- LOCAL_LINUX full Aii suite: BLOCKED; local checkout unavailable and GitHub DNS failed in the prior probe.
- Android ARM64 cross-compile is CI evidence only. No native GGUF model execution or Redmi/Termux receipt is claimed.
- CI uploads a review-only Android ARM64 binary artifact with upstream MIT license and SHA256SUMS. It is not yet packaged by the normal updater or installed under `$HOME/v13/bin`.
- Until QA integrates the artifact into the signed rollback-capable package, the operator fails closed with `NativeReceiverUnavailable` if the binary is absent.

## User impact and safety

- No installed model, model weight, Age/X10, permission, updater setting, Termux data, SQLite data or user source was changed.
- No user action is needed for this code review. A future one-shot device probe requires the reviewed binary to be installed first and an explicit local `--confirm` action.
- This is a diagnostic native input-embedding probe, not proof of semantic use, trained cross-model alignment, learned B3 or whole-system completion.

## Next

1. Run exact-head Python 3.13/3.14 staged Runtime tests, pinned Linux llama.cpp build and Android ARM64 cross-compile.
2. QA reviews the one-line deployer stage-hash update and artifact packaging boundary; no automatic install is enabled here.
3. Boss integrates only after exact-head tests and privacy review pass.
4. QA may then wire the review-only artifact into the normal signed update/rollback package. Only after that should a separate explicit Redmi probe be considered.
