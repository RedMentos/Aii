# Core handoff — native receiver operator-dispatch stage on current QA base

Date: 2026-11-22
Role: Core & Harness
Branch: `core/v14-native-probe-current-qa-20261122`
Base: QA PR #2377 exact head `f64e9943998bba1ec69dcbe342fd865d1a64f990`
Supersedes stale Core stage stack PR #2381 after this replacement PR is opened.

## Product slice

The staged Runtime composes:
1. the pinned recovery builder and native receiver overlay, including the source-bound sender tap and receiver-side native input-effect probe;
2. the exact QA-owned `native_probe_approval.py` source, which binds the active FINAL source, Runtime instance, sender/receiver revisions, manifest hashes, canonical model paths and five-field file identity;
3. the local `:callosum arm-probe` / `:callosum revoke-probe` and one-shot `:callosum native-probe` consumer, with a hard 120-second deadline, cancellation through the Runtime event, synchronous unload and zero production/training authority.

This remains diagnostic-only. It does not enable production B3, trained cross-model alignment, semantic utility, model swaps or weight learning.

## Change in this checkpoint

- Rebased the Core stage-test work by creating a new branch from the exact current QA head `f64e9943998bba1ec69dcbe342fd865d1a64f990`; no force-push or stale-branch rebase.
- Extended `test_native_latent_receiver_stage.py` to assert that Cognition, Callosum, Operator and all native receiver files are in the composed stage and that each final staged byte hash equals `INTEGRATION_STAGE.json`.
- The QA overlay itself already checks that the staged approval module is byte-identical to the reviewed QA source before applying only the command/help overlay. The staged test also checks the nonblocking FIFO and canonical-path/file-identity contract.

## Evidence

- QA base exact head `f64e9943998bba1ec69dcbe342fd865d1a64f990`: native receiver staged-runtime workflow `45077524926` SUCCESS; staged/integrated workflow `45077524947` SUCCESS. These validate the parent QA head, not this new Core test commit.
- Parent staged runtime exercises the real Operator/SQLite approval path and its negative cases, including no-local-approval, one-shot consumption, expiry, restart, model/source drift, byte-identical route redirect, FIFO nonblocking rejection, 120-second deadline cap, native cancellation, and staged manifest integrity.
- LOCAL_LINUX environment: CPython 3.13.5 is available; no Aii checkout is mounted. `git ls-remote https://github.com/RedMentos/Aii.git HEAD` fails with DNS `Could not resolve host: github.com`. Full repository pytest/compile is BLOCKED / NOT_RUN. Do not substitute CI for local proof.
- TERMUX/REDMI: REDMI_UNVERIFIED. The latest owner-read metadata still reports installed base `aed1d2b826290c95c70356b5d8b864b5ef382be4`, auto-update enabled/UP_TO_DATE, but zero valid B1/B2 offers and a slow 38.945-second C3 prefill. This candidate is not installed and no native probe was executed.
- No model/weight download or swap, permission change, UPDATE_REQUEST, remote shell, chat send or device mutation occurred.

## Remaining limits and next action

- The native probe remains an input-consumption/effect diagnostic, not learned latent alignment. B3 stays OFF.
- A path-to-loader TOCTOU remains until the native loader consumes the exact verified descriptor or an immutable snapshot; the current probe remains locally armed, one-shot and diagnostic-only.
- Run the exact PR-head staged/native receiver and integrated workflows for this branch. If green, request independent QA/Boss review and integrate only through the current release chain. A Redmi probe still requires a separate explicit user/device authorization after a compatible release is installed.
