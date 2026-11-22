# Core handoff — explicit remote native-receiver probe allowlist (2026-11-22)

## Ownership and current base

- Owner: Core & Harness
- Branch: `core/v14-remote-native-probe-allowlist-20261122`
- Current release-development base: `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`
- Rebased by a non-force merge commit; the intervening base commit changed only the JEPA Runtime-port test, not these Core files.
- Previous code commit: `aa2d1b55f48012925d83435536009febe0de4ae2`
- Scope: expose the already-staged, one-shot native receiver diagnostic through the existing private owner-read / CHAT_OPERATOR path. This change does not execute the probe.

## Runtime change

The remote operator boundary accepts one additional parameterized command, and only in this exact shape:

`:callosum native-probe <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm`

The actual accepted command contains one concrete sender and receiver role, uses exactly one space between tokens, requires distinct roles, and has no extra flags or suffix. The implementation is an exact full-match allowlist; shell operators, paths, source IDs, newlines, alternate senders and extra payload fields are rejected.

The same validator is used by:
- `remote_chat.send(..., operator=True)`
- private relay `CHAT_OPERATOR` HMAC command verification
- owner-read request creation
- owner-read request validation

Existing owner identity, private-repository, `CHAT_OPERATOR` permission, remote-test consent, one-shot request ID, bounded message size, and local operator `--last-source --confirm` checks remain in force. Normal `CHAT_SEND` still rejects operator-prefixed text. No shell, arbitrary file access, model download/swap, weight update, B3 production routing, or safety-permission change is added.

## Test history and exact evidence

- Initial PR CI exposed a malformed test fixture: the native receiver payload was accidentally nested in the preceding ordinary-chat test and indentation caused collection failure at `test_remote_chat.py:118`.
- Commit `aa2d1b55f48012925d83435536009febe0de4ae2` moved the payload into the native receiver test that consumes it and corrected indentation.
- The earlier exact test commit `33d3ef881ed07b3e0e719aa2e4043a25403f4a90` passed 80 tests + 28 subtests on Python 3.12 and the same on Python 3.14; owner-read focused suites and staged runtime startup/SQLite source-ref tests passed. Staged Runtime and integrated regression also passed on that prior merge base.
- The current release base `c4eb82deec915f65894c20d6ebbaf0ebf58fa335` has its own exact CI history; this rebased PR's current-head CI must be checked before integration.
- LOCAL_FULL_REPOSITORY: BLOCKED — no Aii checkout is present; container GitHub DNS resolution fails. No local full-repository pytest result is claimed.
- TERMUX/REDMI: the latest authenticated private DIAGNOSTICS receipt reports the phone on `9c7a0ec2d58538be8b7fde9476db299f2a5dd7b8`, not this PR and not current release HEAD. It reports `native_probe=SMOKE_PARTIAL`, B1/B2 `TIME_BUDGET` at 53.2/54.2 s, and the last recorded turn at 63.22 s total / 42.48 s TTFT / 34.96 s prefill / 2 generated tokens. This is a prior recorded turn, not a fresh post-update benchmark or proof that either body contributed to a correct answer. No native receiver probe was sent or executed.

## User impact and Canon mapping

This unblocks a user-initiated, bounded measurement of the native receiver input path for B3/Enlightened Space. A successful probe can establish native input consumption/effect for the tested model pair only. It cannot establish learned cross-model alignment, semantic task utility, trained latent coupling, production B3 routing, or AGI.

Canon paths: B1/B2 sender activations, B3/Enlightened receiver path, C3 receiver compatibility, source/consent/audit boundaries. Production B3 remains OFF/SYMBOLIC.

No installed model, weight, permission, dataset, user message, or phone state was changed by this work.

## Research note for the next experiment

- XKV, *Dual-Cache Latent Space Communication between Heterogeneous Language Models* (arXiv:2608.20617, 2026), proposes a trained translator over both source and receiver KV caches, with receiver-position-specific retrieval. This is a research method, not a verified Android-ready implementation.
- *Architecture-Dependent Causal Transfer of Activation States Across Large Language Models* (arXiv:2608.16347, 2026) reports that representation alignment does not reliably imply causal task transfer across model pairs. The next V14 test must therefore measure held-out task utility and negative controls, not only tensor consumption or cosine changes.

## Next integration action

1. Verify the exact current-head CI on this rebased PR.
2. Boss/Integrator reviews and integrates the allowlist + regressions into the release branch.
3. Only after the new release is installed and remote-test consent is confirmed, ask the user separately before issuing one exact `CHAT_OPERATOR` native-probe request.
4. Obtain a fresh device receipt and keep production B3 OFF until paired native activations, source-disjoint labels, same-model parity, shuffled/zero/OOD controls, held-out utility, retention and rollback pass.

## User action

No action is needed now. The probe remains NOT_RUN. Do not send a Termux command, model download/swap, weight update or device action.
## Local one-shot approval follow-up — staged candidate (2026-11-22)

- Added `v13/native_probe_approval.py`: a 120-second, single-use approval bound to the exact active session, latest FINAL user event, source hash/range, generation, sender/receiver model revisions and manifest hashes. It is scoped to the current Runtime object; a Runtime restart invalidates it. No model file is rehashed at arm time; the existing native receiver consumer performs the actual sender/receiver hash checks immediately before native input.
- Added `scripts/integrated_native_probe_approval_candidate_20261122.py`. It composes after the currently staged native receiver and adds:
  - local TTY-only `:callosum arm-probe <sender> <receiver> --last-source --confirm`
  - local `:callosum revoke-probe`
  - remote `:callosum native-probe ...` now consumes the matching one-shot local approval before invoking the native receiver
- The remote allowlist still rejects `arm-probe`; remote `--confirm` alone is insufficient. The approval is consumed atomically before native work, so a crash/failure requires a fresh local arm.
- Added staged Runtime/SQLite tests for no-arm rejection, exact role binding, one-shot consumption, model-revision drift, new-turn/source drift, Runtime restart, expiry and revoke. The stage test applies this overlay only in its isolated candidate directory.
- IMPORTANT: this approval overlay is not yet in the shared production recovery/stage/deployer pin chain. That chain is being handled by Boss/Integrator; do not bypass or independently rewrite it. The active PR remains NOT_RELEASED until the overlay is composed and reviewed there.
- No native receiver probe was executed; no device state, model, weight, permission, or data changed. `LOCAL_FULL_REPOSITORY` remains unavailable in this runner; exact CI on the updated PR is the next test gate.

### Exact CI correction — 2026-11-22

- First staged-runtime run on commit `9bdcf1474928670d7255e82f0be5a52cf7615d02` failed 2/40 focused tests on Python 3.13 and 3.14: the pre-existing Callosum test lacked a FINAL status/local arm, and one new mock returned `None` instead of a packet. Both are test-contract regressions, not native probe failures.
- Corrected the old test fixture to bind model manifest paths/sizes, create a FINAL last-answer fixture, arm the exact B2→C3 pair, and assert the one-shot consumed result. Corrected the fake receiver packet and added a negative non-TTY arm assertion.
- New exact-head CI is pending; the earlier failed run remains preserved as negative evidence.

### Staging boundary hardening — 2026-11-22

- The review overlay now refuses to patch the source tree or any ancestor/descendant of it; it only accepts a separate `SHADOW_REVIEW_ONLY` stage whose recorded source path matches the supplied code tree.
- The stage test includes a negative control that attempts source-tree application and expects a fail-closed rejection.
- Remote bridge comments now state explicitly that remote `--confirm` does not grant local authority; the local TTY arm is separately required.

### Verified checkpoint — 2026-11-22 14:28 UTC

**Code checkpoint:** 33ba4711d47db721076f108101a9eb1faf886052 → 33ba4711d47db721076f108101a9eb1faf886052

- Hardened integrated_native_probe_approval_candidate_20261122.py: validate the review-only stage identity and recorded source before writes; verify every staged file against files_sha256; reject symlinked parent components and symlinks anywhere in the staged tree; use atomic file replacement for staged consumers/manifest.
- The staged native-probe command now has a hard 120-second execution deadline. The local approval remains single-use, source/session/generation/model-bound, 120-second TTL and Runtime-instance-scoped.
- Added negative tests for a symlinked v13 parent, a mismatched stage source, and tampered staged bytes; added a staged dispatcher test proving a huge observer_seconds setting cannot extend the native probe beyond 120 seconds.

**Exact CI on 33ba4711d47db721076f108101a9eb1faf886052:**
- V14 native latent receiver staged runtime: PASS — Python 3.13 and 3.14, 11 outer tests each; pinned Linux llama.cpp API build PASS; Android arm64-v8a cross-compile PASS; public privacy scan CLEAN.
- v13-private-remote-bridge-tests: PASS — 80 tests + 29 subtests on Python 3.12 and again on Python 3.14.
- V13 private owner-read Termux bootstrap: PASS — Python 3.12 and 3.14 jobs.
- V13 staged context and integrated regression: PASS — 424 passed, 3 skipped, 58 subtests on the Python 3.11 runner; JEPA held-out error in that CI experiment moved 0.80315 → 0.75878.
- V13 safe additive candidate tests: SKIPPED by policy; not a pass.
- LOCAL_FULL_REPOSITORY: BLOCKED — no Aii checkout is mounted and git ls-remote cannot resolve GitHub DNS. A separate LOCAL_LINUX_ISOLATED helper reproduction passed the symlink-parent, wrong-source and tampered-hash rejection checks; it is not a full-source pytest run.

**Latest private metadata-only Redmi observation (2026-11-22 14:19 UTC):**
- Installed runtime remains c4eb82deec915f65894c20d6ebbaf0ebf58fa335; runtime and dashboard report UP_TO_DATE, dashboard process RUNNING.
- Five recent turns: C3 prompt 751 tokens, TTFT/prefill 38.945 s, 2 generated tokens. B1 had 4 native attempts / 4 failures; B2 had 2 / 2; 0 valid offers and neither body contributed to the final C3 report. native_probe=SMOKE_PARTIAL; no native latent exchange or semantic use is proven.
- No raw chat text, prompt, path, key or model bytes were copied. No UPDATE_REQUEST, model swap, permission change, shell action or native receiver probe was sent.

**Acceptance boundary:** this branch has a passing staged consumer path and native build/cross-compile evidence, but the local-approval overlay is still NOT in the shared production recovery/stage/deployer pin chain. It is NOT_RELEASED, not installed, and not a Redmi test. The native build does not prove real GGUF inference, learned alignment, semantic utility, trained latent coupling or production B3.

**Next integration owner/action:** Boss/Integrator should compose this exact reviewed overlay after the native-receiver stage in the shared recovery → stage → runtime-deployer chain, refresh all source/blob pins, then run exact CI/readback. Keep production B3 OFF. Only after a release is actually installed may the owner separately decide whether to authorize one exact CHAT_OPERATOR probe. No user action is needed now.


## Model-byte integrity follow-up — 2026-11-22

The local one-shot native-probe approval now verifies the actual installed model bytes against the pinned manifest SHA-256 using a 1 MiB streaming hash (bounded memory), both when arming and when consuming. It also rechecks the resolved model path after hashing and rechecks the approval TTL/current source after potentially slow model verification, before the approval is consumed. A same-size post-arm mutation is a negative regression and must not reach `native_receive`.

This is still only an explicitly armed diagnostic probe: no production routing, weight update, training authority, or Android device proof is added. Exact CI and local test evidence must be recorded on the new head.

## Remote-consumer approval correction — 2026-11-22

The local TTY is required to **arm** or **revoke** the one-shot approval, but not to consume it. The exact, separately consented private `CHAT_OPERATOR` request runs inside the background service and has no interactive TTY; requiring a TTY at consumption made the intended remote diagnostic path unusable. Remote `--confirm` still cannot create or revoke the capability.

The staged `Cognition.native_receive` boundary now independently requires a `CONSUMED` record and rechecks Runtime-instance nonce, active session, latest FINAL event, exact source reference, role pair, installed revisions and current manifest hashes before running the sender tap. It compares both actual model bindings to the locally approved hashes; the existing sender tap checks its pinned model bytes, and the native receiver independently checks receiver bytes before and after decode. Direct calls without a consumed local approval and post-consumption manifest drift fail before native receiver execution.

Regression coverage now includes:
- local TTY required for arm/revoke, but not for consumption after a valid local arm;
- direct receiver invocation without consumed approval rejected before sender tap;
- model revision/hash-manifest drift after consumption rejected;
- the operator consumer succeeds without a TTY after the local arm;
- existing source/session/generation/role/expiry/restart/symlink/hash/negative-control checks remain.

This is still a staged, non-authoritative diagnostic candidate. No production B3 routing, model/weight change, permission change, native receiver execution on Redmi, or deployment is claimed. Full repository tests and exact-head CI must pass before Boss integration; Redmi remains REDMI_UNVERIFIED.


## Core staged integration checkpoint — 2026-11-22 17:05 UTC

**Current Core branch:** PR #2350, `core/v14-native-probe-model-byte-integrity-20261122`, head `3c688a88c2210950b3991494be51b6c0e3890439`. This is a staged candidate based on the separate #2332 remote allowlist branch; it is **NOT_RELEASED** and is not installed on Redmi.

### Executable changes on this head

- Repaired the malformed `revoke()` definition in `native_probe_approval.py`; the prior split signature caused a real Python syntax error.
- Rebound the nested exact-byte chain: native receiver candidate Git blob → recovery builder SHA-256 → stage builder SHA-256 → runtime deployer SHA-256. Readback currently confirms all three links.
- The integrated candidate now dispatches `:callosum arm-probe`, `:callosum native-probe`, and `:callosum revoke-probe`; the global operator help and Callosum help advertise them.
- The local TTY is required to arm or revoke. A separately consented typed consumer may consume a pending local arm without an interactive TTY. The capability is bound to Runtime nonce, active session, latest FINAL source/generation, exact role pair, installed model revisions and manifest SHA-256.
- The approval lifecycle is now PENDING → CONSUMED → USED. The actual native receiver boundary atomically marks USED before native work, so a direct/replayed Python call cannot reuse the one-shot approval. A CONSUMED-but-not-yet-used approval cannot be overwritten by a new arm; it must be revoked or expire. Revoke can cancel PENDING or CONSUMED.
- Native probe execution remains hard-capped at 120 seconds, production routing OFF, training authority 0, receiver authority 0, and semantic utility unproven.

### Test evidence and environment

- LOCAL_LINUX / isolated synthetic Python stubs: **7/7** approval-binding tests PASS (exact source/session/event/role, manifest hash, restart, expiry, revoke, no-arm).
- LOCAL_LINUX / isolated synthetic state-machine tests: **5/5** PASS (PENDING/CONSUMED overwrite refusal, expiry, revoke, USED replay refusal).
- These are isolated reproductions, **not** a full Aii pytest run and not a native GGUF execution.
- Exact-head GitHub workflows for `3c688a88c2210950b3991494be51b6c0e3890439` are queued; no CI PASS is claimed yet. The workflow matrix includes Python 3.13/3.14, pinned Linux llama.cpp build, Android arm64 cross-compile, staged/integrated regression, runtime deployment integrity and private owner-read bootstrap.
- LOCAL_FULL_REPOSITORY remains BLOCKED: no Aii checkout is mounted and local `git ls-remote` cannot resolve GitHub DNS.

### Latest private Redmi evidence (metadata only)

- PIPELINE_STATUS #579 and #582: installed SHA remains `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`; auto-update enabled, Runtime/Dashboard report UP_TO_DATE, last_error NONE. This is updater state, not proof that the model runtime is healthy.
- DIAGNOSTICS #580: last recorded turn FINAL, 57.74 s total, 41.63 s TTFT, 751 prompt tokens and 2 generated tokens; B1/B2 both TIME_BUDGET at 53.2/54.2 s, C3 3.1 s. This is a recorded prior turn, not a new post-update test.
- HEALTH #581: status OK but Runtime state UNAVAILABLE; 1,414 MiB available RAM and 1,568 MiB free storage. Do not infer a working chat process from UP_TO_DATE alone.
- No native receiver probe was sent or executed. No model, weight, permission, updater, database or device state was changed.

### Remaining integration and actual latent-coupling gap

- #2343 Boss integration head `9a1424bbf11f3306ce1a50f1e88cbb5c3765bca2` and #2346 Perception paired-tap head `81d225af972e8b3d6b645aba09cd01ccac5fa020` still have shared staged/deployer pin failures; #2346's focused B3 tests are green, but that is synthetic shadow-optimizer evidence, not native Redmi coupling. Rebase/re-pin this Core candidate only after the shared composer base is stable; do not overwrite their files.
- The current B3 `Bridge.receive()` returns a task/readout classifier, not receiver input vectors. The current native receiver measures llama.cpp input consumption/effect and negative controls, but not semantic task utility. Neither proves a trained latent communication channel.
- Next Core implementation: a read-only, row-bounded receiver input-embedding extractor against the exact pinned llama.cpp revision `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`, using the internal `model->tok_embd` tensor and checked `ggml_backend_tensor_get` / `ggml_type_traits::to_float` extraction. Do not call the existing full-matrix dequantizer on Android. Then coordinate source-span-aligned B1/B2 pairs, train separate directional low-rank projectors, and measure same-model parity, zero/shuffle/no-message/symbolic controls, source-disjoint held-out task output, retention and rollback. The extractor/projector is **not implemented** yet.
- Do not authorize a device probe until exact-head CI is green, Boss has integrated/released the candidate, the installed SHA is privately confirmed, and the user separately approves that one exact probe.

**User action: none now.** No manual Termux command, UPDATE_REQUEST, model download/swap, weight change or permission change is required.
