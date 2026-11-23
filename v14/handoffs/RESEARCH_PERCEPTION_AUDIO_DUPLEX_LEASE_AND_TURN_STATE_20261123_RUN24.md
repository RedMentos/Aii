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


## Run 24b — exact test, deployment and device readback (2026-11-23)

- Code/test SHA: `2aea5606b871e50f594a508880977bd03a6f5c9f`; test blob `420704e2e13c6a4d0af829d1e111d8fa588bd067`. Added both thread-bound lease and simulated process-epoch restart negative controls.
- Exact push CI on that code SHA: `python -m pytest -q v13/code/tests/test_audio_duplex_bridge.py` — **17 passed on Python 3.13 (71.19 s), 17 passed on Python 3.14 (60.15 s)**. Offline Python 3.11 and 3.14 PASS; offline-bridge-security PASS; privacy PASS; staged-runtime PASS; consumer Python 3.13 PASS. Consumer Python 3.14 and integrated-regression were still IN_PROGRESS at the last poll. PR checks are not yet fully green.
- LOCAL_LINUX: both added test functions AST/syntax parse PASS. The exact AudioConsentLease class was isolated from the branch and exercised: same-thread match true, worker-thread match false (PASS). Full Aii checkout/full pytest remain BLOCKED: no mounted checkout and github.com DNS failure.
- Fresh private PIPELINE_STATUS #832 (17:38:26 UTC): auto_enabled=true; dashboard/runtime UP_TO_DATE; last_error=NONE; installed SHA `8d93236c753f0194224c19edc7411d8d7082b1d6`. This proves the normal updater installed the current release-development base, not this unmerged PR candidate.
- Latest sanitized #1904 diagnostics (17:03 UTC) say AI runtime STOPPED_BY_USER, autostart=false, model process STOPPED. Preserve that state. No restart, CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell or user-data action was performed. Last stored turn is not a new test: 6.295 s total, 2.046 s TTFT, 358 admitted prompt tokens, 7 generated; arithmetic remains failed/incomplete (2+2→2); B1/B2 remain TIME_BUDGET at 53.2/54.2 s; C3 probe 3.1 s; native probe SMOKE_PARTIAL; internal organ hypotheses appeared in user-visible console output. No raw user text is copied here.
- The fresh receipt does not establish model residency, microphone capture, voice behavior or correctness. Redmi runtime remains STOPPED_BY_USER; no new E2E chat or Android AudioRecord test was attempted.
- R-116 full-paper review: HiThink Turn's separate validity/intent/playback state is conceptually useful but its Qwen3-ASR-1.7B model is not a mobile candidate. Voice-Light's learned endpoint head underperformed Silero on locked human holdouts; no code was reused because the official repository declares no license. sherpa-onnx 20M Zipformer is only a possible optional ASR teacher (Apache-2.0, ~26.5 MB int8 core); no model was downloaded or changed.
- PR #2448 remains DRAFT / NOT_RELEASED. No user action is required. Boss was notified to sync the fresh device receipt and STOPPED_BY_USER state into the Boss-owned Next Action/Work Board; those shared files were not overwritten while Boss PR #2443 actively edits them.

### Next executable step

Finish exact-head consumer 3.14 and integrated-regression CI. If all checks pass, hand PR #2448 to independent Boss/QA review. After merge, Core/QA must connect this caller-supplied PCM bridge to the signed companion provider and an actual audible-playback acknowledgement path; preserve default capture OFF and verify permission, revocation, zeroization, lifecycle, restart and rollback before any Android microphone test.
