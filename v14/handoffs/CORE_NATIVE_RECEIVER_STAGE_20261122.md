# Core & Harness — staged native receiver probe (current Boss base)

**Date:** 2026-11-22  
**Base:** Boss PR #2288 at `b41814484b934b39ce94413743f8685e498a095e`  
**Branch:** `core/v14-native-receiver-b418-20261122`  
**Status:** DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Function

Adds an explicit one-shot `:callosum native-probe <sender> <receiver> --last-source --confirm` path for a source-bound B1/B2 tap into a separately loaded B1/B2/C3 receiver through pinned llama.cpp `llama_batch.embd -> llama_decode -> llama_get_embeddings_ith`. The sender runner is unloaded before the receiver model is loaded, so the probe does not intentionally keep two dense model copies resident. It records only source/model IDs and hashes, dimensions, position metadata, decode status and input-effect/negative-control metrics.

The result remains a non-authoritative `LatentReceiverPacket`: `production_route=false`, `semantic_use_proven=false`, `training_authority=0`, `native_receiver_authority=0`. It does not enable B3 production routing, trained alignment, model swaps or weight learning. The binary is separately built and is not auto-installed by the updater; the operator fails closed until the locally installed pinned executable is present.

## Rebase repairs

The prior #2300 branch failed before stage composition because the outer/stage/deployer pins were stale. This current-base branch:
- pins the exact current raw Cognition, Callosum, Runners, Models, Contracts and Operator files;
- updates the native wrapper/CMake/C++/README SHA-256 pins to the exact fetched bytes;
- adjusts the Callosum operator anchor to preserve the current `promote` result shape;
- pins the current base recovery builder blob and C4 receipt, then updates the wrapper → stage → deployer SHA-256 chain.

## Provenance

Upstream: `ggml-org/llama.cpp` at `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`, declared MIT. The workflow independently checks the upstream LICENSE, builds Linux and Android `arm64-v8a` binaries, runs native self-test, and uploads a review-only artifact. The previous #2300 workflow had Linux native build and Android ARM64 cross-compile PASS; its Python stage jobs failed on the stale integrated-builder hash before reaching this overlay. This current rebased head must rerun all jobs.

## Exact source pins

- Native receiver overlay SHA-256: `9e3562775eb07d4384cd0d6901fd6f2e957346b297ff82c2a8fec09ff0771007`
- Outer recovery builder SHA-256: `668392f6f661fad4cc4dfaa2ac6972a99cc3eea5278aafbc49504711dfccd4a4`
- Integrated stage builder SHA-256: `0d4fd8760ea49bd12ba4696e449ab33548f266984baa490a46786f847827dc3c`
- runtime_deploy.STAGER_SHA256: exact match to `0d4fd8760ea49bd12ba4696e449ab33548f266984baa490a46786f847827dc3c`
- Current Boss base builder Git blob: `a142f51814a521183416619b763b3a6202fe6d67`
- Current C4 receipt SHA-256: `0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3`

## Evidence boundary

- LOCAL_LINUX full Aii checkout: BLOCKED; no local repository checkout and GitHub DNS resolution fails from this runner.
- Exact-head GitHub Actions on this rebased PR: pending.
- Previous PR #2300 native Linux build and Android ARM64 cross-compile: PASS, but its Python staging tests failed on the old outer-builder hash before the new overlay ran.
- No actual GGUF model was loaded, no native model inference/semantic utility was measured, no trained B1→B2 adapter or B3 production route is proven.
- TERMUX/REDMI: REDMI_UNVERIFIED. No connected authorized device receipt or installed binary exists in this run.
- No model, weights, Age, permission, updater, database or user data changed.

## Next

Run exact PR CI. If green, retain the probe as diagnostic-only and use an explicitly installed/pinned native binary plus an approved local model only when the user chooses to run the operator probe. Any future promotion requires separate trained alignment, negative controls, semantic task utility, retention, rollback and real Redmi measurements.
