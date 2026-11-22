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