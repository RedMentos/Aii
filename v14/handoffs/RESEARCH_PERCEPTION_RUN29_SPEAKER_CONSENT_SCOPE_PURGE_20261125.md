# Research & Perception — Run 29: RAW EAR speaker consent-scope eviction

Date: 2026-11-25
Branch: `research-perception/v14-speaker-consent-scope-purge-20261125-run29b`
Parent branch: `research-perception/v14-audio-speaker-window-order-20261125-run27`
Parent PR: #2487
Child PR: #2491 — https://github.com/RedMentos/Aii/pull/2491

## Defect and Canon path

The RAW EAR speaker registry was already keyed by source, generation and a hash of the current provider-validated consent receipt. A new receipt selected a fresh state, so old vectors did not affect the new result, but prior same-source/same-generation keys remained in the process-local LRU until unrelated eviction. This violated the intended per-consent-epoch lifetime and differed from the temporal voice registry, which resets on scope rotation.

Canon: A0/A-plane RAW EAR → A4 acoustic speaker-change evidence; consent/revocation; process-local memory lifetime; no speaker identity authority.

## Runtime change

- In `v13/code/v13/audio_speaker_evidence.py`, updating a source/generation with a different scope now removes all older keys for that same source/generation before reading/creating the current state.
- This removes both old hashed scopes and legacy unscoped entries. Different sources are untouched. Existing different-generation cleanup remains unchanged.
- Same-generation scope replacement returns `reset_reason=CONSENT_SCOPE_CHANGED`.
- The exact consent receipt remains hashed by `audio_voice_cues.py`; neither receipt nor fingerprint is added to the packet. Embeddings remain process-local float32 arrays; no PCM/vector persistence was introduced.
- No calibration, identity, learning, interrupt or action authority changed. A4 remains DEFER without a verified model-bound calibration artifact.

## Exact commits and readback

- Code commit: `8162f40ff52688351dcf52ab50b1543ecbdfe5bd`; source blob `ffcd1ecb679f38ae5b6e90cdb3284d7f94990232`.
- Regression commit / current code-test head before this handoff: `38f0ef5fa46651e157c365a490e5faa16c33feb9`; test blob `93425a42c6c8fd2c9d5cca16ae5255b659d340bd`.
- Parent branch head at child-PR creation: `cbf3bca17797f52c889b672baef5b7fd5b7deb80`.
- GitHub PR #2491 is DRAFT / NOT_RELEASED and explicitly targets parent branch #2487, not the release branch. Tested code/test head is `38f0ef5fa46651e157c365a490e5faa16c33feb9`; docs-only follow-up commits are recorded in the PR.

## Tests

- LOCAL_LINUX isolated state-machine reproduction: **7/7 PASS**. Covered same-scope retention; scoped→new-scoped eviction; unscoped→scoped and scoped→unscoped eviction; cross-source isolation; generation-change cleanup; and concurrent scope rotations remaining bounded to one state.
- This was an isolated reproduction of the state transition, not execution of the exact repository module.
- Full local Aii checkout/pytest: **BLOCKED / NOT_RUN**. No repository checkout is mounted and `git ls-remote` cannot resolve GitHub DNS in this execution container.
- Exact-head CI on #2491 head `38f0ef5fa46651e157c365a490e5faa16c33feb9`:
  - RAW EAR fastpath run 45571203618: **PASS** on Python 3.13 and 3.14; each job reports 148 passed, exact py_compile, synthetic benchmark (`device_benchmark=false`) and clean privacy scan.
  - FASTDIAR adapter-consumer run 45571203750: **PASS** on Python 3.13 and 3.14; each job reports 108 passed and exact py_compile.
  - RAW EAR/WebRTC/libfvad comparator run 45571203673: **PASS** on Python 3.13 and 3.14, including pinned comparator/native-library build and synthetic ABI checks.
  - staged/integrated run 45571203720: **FAIL**. Both staged-runtime and integrated-regression fail at the Core-owned recovery builder's controller-guard SHA mismatch (`86ad7838…`); two-checkout migration returns PARTIAL instead of UPDATED. This is the same Core pin dependency tracked by #2482/#2483, not a failure in the two Perception paths. Do not weaken the source hash.
- CI is not local Linux or Android evidence.

## Research — R-121

Yu, Liu & Qian, “When Forgetting Looks Like Improvement: Metric Masking in Streaming Diarizer Adaptation and the Price of Rehearsal,” arXiv:2610.08828, submitted 2026-09-26; preprint, no peer-reviewed acceptance established. Full arXiv HTML was reviewed.

The study adapts a 117M-parameter Streaming Sortformer v2 on 7.5 hours of two-party conversation (153 training sessions, 36 speaker-disjoint holdout sessions; however, the holdout had participated in earlier recipe development). Across six corpora, detection gains could coexist with speaker-attribution/temporal-consistency loss: on AMI, confusion rose from 7.75% to 21.46% even as miss/false-alarm components improved. Rehearsal reduced some identity degradation but sacrificed transfer on PriMock57 (DER 8.42%→19.40%). Three Expert seeds were reported; uncertainty remains conditional on checkpoints, thresholds and grouping.

V14 implication: report speaker-activity detection and identity/temporal consistency separately; do not treat a better aggregate DER or a similarity score as identity proof. Keep session/consent memory bounded and discard it on scope rotation. No paper code, model or data was reused. The arXiv page does not establish a separate code/weight license.

## Device, deployment and risks

- TERMUX/REDMI: **REDMI_UNVERIFIED**; no live microphone or phone access was used.
- No private relay, CHAT_SEND, UPDATE_REQUEST, shell, model/weight download/swap, permission change or user-data mutation.
- GitHub push/PR is not deployment. Release: **NOT_RELEASED**.
- The parent branch still carries strict Core source-pin/staged-integration dependencies; do not weaken source hashes. #2491 must be reviewed/merged into #2487 before the parent can be integrated.

## Next executable step

Read the completed exact-head CI for #2491. If the focused tests pass, request independent review of this child. Then let Core/QA resolve the #2482/#2483 source-pin chain and rerun staged/integrated tests on the exact combined head. Continue separate source-disjoint calibration and overlap/silence/return controls; keep speaker identity and all learning/action authority OFF.
