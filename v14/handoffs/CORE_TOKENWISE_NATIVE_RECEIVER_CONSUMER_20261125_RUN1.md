# Core & Harness Run 1 — tokenwise native receiver consumer

Date: 2026-11-25
Owner: Core & Harness
Branch: `core/v14-tokenwise-native-receiver-consumer-20261125-run1`
PR: https://github.com/RedMentos/Aii/pull/2512
Current code head: `6ff13917a9736a292716becdb2e50a1ac7f9b288`
Base: Core #2510 (`df7a35ca504af65a17b91d29603d785f18e44dd0`)
Second parent / helper source: Perception #2511 (`68ce8ca8122fba9b0063a4da89a117377a1b9e92`)

## Implemented

- Added `v13/code/v13/native_tokenwise_receiver_probe.py`.
- `fit_and_probe_native_tokenwise_cohort` fits an in-memory session-disjoint TOKENWISE adapter and only probes a pair record that belongs to a declared holdout session.
- `probe_native_tokenwise_candidate` requires the current authoritative source/event/session/generation, exact sender/receiver model revisions and file identities, a live exclusive Runtime lease, empty queue and zero known managed model processes.
- It builds the Perception anchor-preserving packet, checks authority-zero status, validates finite float32 rows and their digest, consumes the separate existing local-TTY `NATIVE_RECEIVER` approval, then calls the pinned native receiver probe.
- Audit stores hashes and numeric metrics only. Pair vectors and adapter remain in memory; no production B3 route, semantic utility, model-weight update or persistent adapter is claimed.

## Tests and evidence

- Core #2510 exact CI: 7/7 observed workflows SUCCESS.
- Perception #2511 exact CI: staged-runtime and integrated-regression SUCCESS.
- Earlier #2512 head `27c4788`: compile PASS on Python 3.13/3.14; focused tests 18 PASS / 1 FAIL. The only failure was a Path-vs-string assertion in the new test, corrected at `6ff1391`.
- Exact-head CI for `6ff1391`: QUEUED at checkpoint; must be read before review.
- LOCAL_LINUX full Aii checkout: BLOCKED; `git ls-remote` failed DNS. No local repository pytest/native build.
- REDMI_UNVERIFIED. No authorized live device receipt, native GGUF probe, app install or deployment.

## Next exact work

1. Poll PR #2512 head `6ff13917a9736a292716becdb2e50a1ac7f9b288` workflows and check runs; fix any failure and retest.
2. Ask Boss/Integrator to reconcile the #2510/#2511 dependency stack; do not merge another owner's branch or change their files.
3. When an authorized native environment is reachable, run a one-shot receiver diagnostic with explicit local TTY approval and a real held-out record; record native input-consumed/effect and zero/shuffle/repeat controls.
4. Keep B3 OFF/diagnostic until task-level held-out semantic utility, OOD, retention, restart and rollback all pass. No device action is currently required.
