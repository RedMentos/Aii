# Research/Perception handoff — RAW EAR speaker evidence
Date: 2026-11-22
Owner: Research & Perception
Current candidate: PR #2293 (DRAFT, NOT_RELEASED)

## Current branch and dependency
- Branch: `research-perception/v14-raw-ear-speaker-currentboss-20261122-r2`
- Code head: `be17014546fa50ddd4513b7c42ec7159267344f4`
- Base: Boss branch `boss/v14-recall-store-pin-rebind-20261122` at `f0d3c848dfb1d65e282f065233adbe3c9205e439`
- The previous stale #2275-on-#2258 PR and duplicate #2292 were closed as superseded. No force-push.

## What the candidate changes
- Adds the optional `audio_speaker_evidence.py` consumer for caller-supplied, source/generation-bound frame embeddings.
- The history registry snapshots pre-batch state for every frame in an incoming batch; the peak change evidence is retained for A4 even if the batch returns to its original speaker embedding. C3 receives a bounded summary.
- PerceptPacket output contains scalar similarity/timing/provenance only. Embedding vectors remain process-local; no speaker identity, archive linking, learning authority or Android action authority.
- Optional NumPy pitch backend remains explicit opt-in; Python remains the default.
- Integrated audio builder now pins `audio_voice_cues.py` and `audio_speaker_evidence.py`; recovery-wrapper → stage-builder → runtime-deployer SHA chain was recalculated and read back.

## Exact source and pin evidence
- `audio_voice_cues.py` blob: `9b6bafe1e02b3f49503d57399b43248b9e6d8bb1`
- `audio_speaker_evidence.py` blob: `b869108a7828c4601fc179a645d134f55c1eacc2`
- integrated audio builder blob: `118a63bfca4c163cb7bb96a2c84d8e81d9abf08e`
- recovery wrapper SHA-256: `bc255bc2e1438b8acc4e77f69e0ae6bb25a200d51bb95b343588e5dc39daf2c6`
- stage builder SHA-256: `0303a36409bb3e846bc2ee5558166878adce2d96f3cf13f72bdaf9c640fd3e79`
- runtime deployer `STAGER_SHA256` equals the stage builder SHA-256; VAD workflow pins the current voice-cue blob.

## Tests and exact results
- **PASS** GitHub Actions run `44969991498`: CPython 3.13 and 3.14; compile, backend parity, A5→A4→C3 consumer tests, deterministic synthetic benchmark, changed-public-content privacy scan.
- **PASS** GitHub Actions run `44969991513`: CPython 3.13 and 3.14; native libfvad build, exact source-blob checks and synthetic ABI/benchmark comparison.
- **PASS** GitHub Actions run `44969991505`: offline runtime-deployment integrity.
- **FAIL / baseline blocker** GitHub Actions run `44969991457`: staged runtime and integrated regression fail at `local-error pre-rebind semantic binding mismatch` in `termux_runtime_recovery_candidate_20261112.py:313`. The same failure is present on the unmodified Boss base head `f0d3c848dfb1d65e282f065233adbe3c9205e439`, run `44969679441`; this is not caused by the RAW EAR overlay. The Core-owned semantic dependency pin must be repaired before Perception can obtain a green full integration result. The staged job on #2293 reported 19 failed, 231 passed, 10 skipped, 2 errors, 41 subtests passed.
- **LOCAL_LINUX:** earlier CPython 3.13.5 x86_64 algorithm-only reproduction passed A→B→A peak retention, 1s/2s batch invariance, same-speaker, threshold-absent and unvoiced controls on code/test head `2996153a1244afa318e084df419b01a53095aeda`. Full Aii local checkout was unavailable in this execution, so no full local repository test is claimed.
- **TERMUX/REDMI:** no live receipt; no microphone, model inference, native device test or Redmi benchmark. `REDMI_UNVERIFIED`.

## Research notes
- R-058 FASTDIAR (arXiv:2610.02941) and R-059 ReDimNet2 are retained in the research ledger. FASTDIAR is frame-level and streaming; its checkpoint license still needs independent confirmation. ReDimNet2 is utterance-level and is not a streaming replacement.
- R-061 eDIAR (arXiv:2611.18529, 2026-11-13) full 18-page paper and official repository README/LICENSE reviewed. It uses a fixed-slot head plus 256-D embeddings and spherical e-means only after slot capacity is exhausted; 90s bounded re-clustering and 10s label revision. Reported setup uses 99.2M Nemotron-3 + 6.6M WeSpeaker, CUDA GPU, ~1.9 GiB CPU RSS, 850 MiB GPU, and 4.5 GiB for 1.16M-frame archive linking. Not a Redmi candidate. Limitations: English-only, small real-corpus set plus synthetic conversations, no far-field, rapid-turn long meetings can exceed the head; cross-recording linking has re-identification risk and needs consent.
- Licenses: eDIAR code Apache-2.0; vendored e-means MIT; Nemotron-3 OpenMDW-1.1; WeSpeaker ResNet34-LM CC-BY-4.0. No weights downloaded or reused.
- e-means arXiv:2611.09501 and Faiss implementation were reviewed at abstract/repository level only, not full-paper read.

## Deployment and next action
- No release created; no updater request; no device mutation.
- `RELEASE_SHA=NOT_RELEASED`; GitHub deployment-integrity PASS is not phone deployment.
- Next owner: Core fixes the baseline `local-error pre-rebind semantic binding mismatch` on the Boss integration branch. Then Perception rebases #2293 onto the verified Core head and reruns exact staged/integrated tests. QA reviews consent, revocation and no-vector-persistence behavior.
- User decision: none; no action required.


## Final CI checkpoint — 2026-11-22 01:17 UTC

- Current code/test SHA: `d7f3842d3c0b6f5129f5945eacd770115c7af78e`; PR #2293 remains DRAFT on Boss base `f0d3c848dfb1d65e282f065233adbe3c9205e439`.
- PASS: #44970593770 RAW EAR 3.13/3.14 (57 tests on 3.13, exact frame-age derivation); #44970593769 VAD/libfvad 3.13/3.14; #44970593754 deployer integrity.
- FAIL / baseline: #44970593815 staged/integrated, same `local-error pre-rebind semantic binding mismatch` on unmodified base #44969679441. #44970593848 updater migration PARTIAL; #44970593805 owner-read bootstrap stage failure; #44970593878 Lab Age/WebView stage failure.
- Benchmark #44970593770: synthetic x86_64 only; NumPy 9.0642 ms median vs Python 191.6681 ms, speaker evidence 0.8955 ms; no model inference. Not Redmi proof.
- Last private device snapshot #115 (updated 2026-11-18T11:30:53Z) reports auto_enabled=true, last_result=PARTIAL, last_success_utc=2026-11-18T07:54:05Z and updated_commit=89333289b8cd50da92cbf7074c9ef689a2972dbf; it is stale. New PIPELINE_STATUS request #454 remains open with no receipt. No release/deployment; `NOT_RELEASED`, `REDMI_UNVERIFIED`.
- Next owner: Core resolves the baseline semantic pre-rebind pin mismatch; Perception rebases and reruns; QA reviews privacy/consent and revocation. No user action required.


## Audio-only ingress addition — 2026-11-22 02:35 CET

- New file: v13/code/v13/audio_input.py; public entrypoint submit_audio_only(runtime, audio_window).
- The adapter submits a fixed no-transcript marker and caller-supplied PCM16 to the existing staged Runtime audio_window path. It rejects absent/failed consent preflight, missing linearizable guard, missing two-phase revocation subscription, invalid/oversized PCM, invalid timestamps/source IDs and incompatible text-only Runtime. It preserves PROVISIONAL/FINAL and does not invoke ASR, open a microphone, store PCM or download a model.
- Exact GitHub blobs read back: module 1e9daddcb5dfd8bfb7911090218b4eaf1f103d41, tests b6b1202904efbc417971db6c0d9e3ba0664eef84. LOCAL_LINUX isolated py_compile PASS; pytest 7/7 PASS. This is not a full Runtime E2E.
- Workflow changes are in PR #2293 current head e85b7398b1fce84423583abf01e1389507612818; focused workflow #44972070097 was pending at checkpoint. Earlier speaker-evidence head d7f3842 passed 57 tests on Python 3.13/3.14; current staged/integrated still fails at Core's pre-rebind semantic pin mismatch on unmodified Boss base f0d3c848.
- Full local checkout unavailable: git ls-remote https://github.com/RedMentos/Aii.git HEAD returned Could not resolve host: github.com. No local full Runtime test was run.
- R-063 added: FASTDIAR full paper read; MIT code, checkpoint license not verified; speech-core Apache-2.0 C++17/Android reviewed as a possible low-level VAD/AEC/cancel layer only. No model or dependency downloaded.
- No microphone, Android AudioRecord, TTS effector, barge-in, Redmi or native model proof. No release or updater action. Next: Core fixes the pin blocker; Perception rebases and adds staged audio-only Runtime proof, then coordinates Android caller wiring.


## Exact-head CI follow-up — 2026-11-22 02:37 CET

- Current PR #2293 branch head after docs: 4f3d28982b376445b7846509248097b11c90593b; tested code/workflow head: e85b7398b1fce84423583abf01e1389507612818; base f0d3c848dfb1d65e282f065233adbe3c9205e439.
- RAW EAR fastpath #44972070097: PASS, 64 tests on Python 3.13 (8.10s) and 3.14 (12.25s); includes 7 new audio-only ingress tests, compile, A5→A4→C3 consumer and privacy scan.
- VAD/libfvad #44972070081: PASS, 8 tests on both Python versions; native libfvad 13/13. Runtime deploy integrity #44972070113: PASS.
- Staged/integrated #44972070090: FAIL at Core-owned local-error pre-rebind semantic pin mismatch (recovery candidate line 313); staged job 19 failed / 231 passed / 10 skipped / 2 errors / 41 subtests, integrated job 1 failed. Same failure on unchanged Boss base in #44969679441. Migration #44972070092 returns PARTIAL; Lab Age/WebView #44972070087 and owner-read #44972070168 fail at stage.
- Boss PR #2288 comment 7072186155 clarified the guard-output generation; Perception corrected its follow-up in #7072323336. Correct sequence: capture guard_semantic_sha and guard_local_error_pin immediately after control_guard.apply_sources(), assert equality, then rebind from the guard-output pin to final_semantic_sha after the Store rebind. Core files untouched.
- LOCAL_LINUX isolated audio_input.py py_compile PASS and pytest 7/7 PASS; exact blobs module 1e9daddcb5dfd8bfb7911090218b4eaf1f103d41 and test b6b1202904efbc417971db6c0d9e3ba0664eef84. Full repo checkout blocked by DNS; no full local Runtime test.
- No audio-only Runtime E2E on current base, no microphone/AudioRecord, no Android TTS, no barge-in, no native speaker model, no Redmi. No release, updater request or device mutation.
- Next: Core resolves the guard-generation pin mismatch; Perception rebases #2293 and adds staged Runtime audio-only E2E, then coordinates Android caller wiring with Core/QA.


## Core pin-generation correction — 2026-11-22

Boss comment #7072186155 clarified that Record-Only control_guard.apply_sources() rewrites both world_semantic_evidence_candidate.py and the local-error consumer pin. The correct expected value for the later Store rebind is therefore the GUARD-OUTPUT local-error pin, not the original base pin. Sequence: capture guard_semantic_sha and guard_local_error_pin immediately after the guard; assert equality; after Store rebind, rebind from guard_local_error_pin to final_semantic_sha; keep the final exact-pin check. Perception corrected its follow-up comment #7072323336 accordingly. No Core-owned file was changed.
