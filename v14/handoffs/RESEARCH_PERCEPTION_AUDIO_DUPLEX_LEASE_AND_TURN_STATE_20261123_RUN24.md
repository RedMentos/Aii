# Research & Perception — audio lease boundary and selective turn-state research — 2026-11-23

- Repository: RedMentos/Aii
- PR: https://github.com/RedMentos/Aii/pull/2448
- Branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- Parent exact branch head before this checkpoint: 81dbcb22a483525a13f7bd4f250062615b8020ff
- Test commit: 6225634ccbbb70ce60cc52cbb801ed5ed1d208c7
- Research-ledger commit: 5bc940e64222604ed92cc38607f54f2d577d0537

## Implementation

Added `test_audio_consent_lease_cannot_be_reused_from_another_thread` to `v13/code/tests/test_audio_duplex_bridge.py`.

The test builds a real synthetic Runtime turn, persists a source-bound PCM16 RAW EAR packet and temporal receipt while holding the same `AudioConsentLease`, then attempts dispatch from another thread. It requires a PermissionError before cancellation and verifies the original Runtime answer remains FINAL. This exercises the lease's thread-bound invariant at the actual bridge consumer boundary rather than only testing the CAS replay helper.

No provider, microphone, Android permission, model, weight, user data or deployment setting was changed.

## Research

Added R-116 to `v14/V14_RESEARCH_LEDGER.md` after full primary-source review:

- HiThink Turn, arXiv:2609.34096 (2026-09-28): separates audio validity, response/backchannel/interruption intent and system playback state; 240-ms chunks; Qwen3-ASR-1.7B LoRA; 7,633h training / 5.552M samples / 8 H100. Useful state decomposition, not a mobile model candidate.
- Voice-Light, arXiv:2609.20995 (2026-09-17): hybrid onset + reversible playback + small causal adapter + private speculation + audible-only history. Its learned endpoint head underperformed Silero on locked human data (12.53% vs 95.60% EOT recall at 2.70% false cutoffs). Official repository has no declared license/root LICENSE; no code or weights reused.
- V14 implication: keep RAW EAR onset separate from semantic intent and endpoint; default auto remains non-cancelling; do not promote a learned head without source/session-disjoint locked evaluation. The current text Runtime still has no audible speech effector/acknowledged-playback path.

## Verification and boundaries

- LOCAL_LINUX full repository: BLOCKED. The active container has no Aii checkout; `git ls-remote https://github.com/RedMentos/Aii.git HEAD` fails because `github.com` DNS does not resolve. No local pytest/compile result is claimed for this new test.
- Exact GitHub CI on parent 81dbcb22a483525a13f7bd4f250062615b8020ff: audio-duplex-bridge Python 3.13 and 3.14 PASS; offline Python 3.14 PASS; privacy PASS. Staged Runtime/integrated regression were still in progress and consumer/offline 3.11 jobs queued at the last poll. Those results do not cover the new test commit.
- New exact head after this checkpoint: 5bc940e64222604ed92cc38607f54f2d577d0537. Its CI must be polled before review/merge.
- TERMUX/REDMI: REDMI_UNVERIFIED. No connected authorized handset or private fresh receipt was available. No AudioRecord provider or audible playback was exercised.
- Runtime scope: the bridge is still a caller-supplied PCM helper. It is not a continuous microphone provider, not a normal Runtime.submit call site, and not complete full-duplex voice I/O.
- Release/deployment: NOT_RELEASED. GitHub push is not deployment. No UPDATE_REQUEST, model/weight swap, permission change or user-data mutation.

## Next executable step

Poll exact-head CI for 5bc940e. If green, request independent Boss/QA review; then Core/QA must wire the bridge to the signed companion provider and an actual audible-playback/acknowledgement path. Keep capture and B3 production coupling OFF until the provider, revocation, lifecycle, zeroization, rollback and explicit Android permission gates are verified.
