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
- The adapter submits a fixed no-transcript marker and caller-supplied PCM16 to the existing staged Runtime audio_window path. The candidate builder attaches consent-bound acoustic context to B1/B2/C3 QueryPackets with source provenance and per-consumer rechecks; this is code-level only until staged/integrated passes, and is not a trained audio projector or native latent transfer. It rejects absent/failed consent preflight, missing linearizable guard, missing two-phase revocation subscription, invalid/oversized PCM, invalid timestamps/source IDs and incompatible text-only Runtime. It preserves PROVISIONAL/FINAL and does not invoke ASR, open a microphone, store PCM or download a model.
- Exact GitHub blobs read back: module 1e9daddcb5dfd8bfb7911090218b4eaf1f103d41, tests b6b1202904efbc417971db6c0d9e3ba0664eef84. LOCAL_LINUX isolated py_compile PASS; pytest 7/7 PASS. This is not a full Runtime E2E.
- Workflow changes are in PR #2293 current head e85b7398b1fce84423583abf01e1389507612818; focused workflow #44972070097 was pending at checkpoint. Earlier speaker-evidence head d7f3842 passed 57 tests on Python 3.13/3.14; current staged/integrated still fails at Core's pre-rebind semantic pin mismatch on unmodified Boss base f0d3c848.
- Full local checkout unavailable: git ls-remote https://github.com/RedMentos/Aii.git HEAD returned Could not resolve host: github.com. No local full Runtime test was run.
- R-063 adds FASTDIAR full-paper evidence (MIT code, checkpoint license unverified); speech-core turn/AEC/cancel details are a follow-up to R-033, not a new dependency candidate. No model or dependency downloaded.
- No microphone, Android AudioRecord, TTS effector, barge-in, Redmi or native model proof. No release or updater action. Next: Core fixes the pin blocker; Perception rebases and adds staged audio-only Runtime proof, then coordinates Android caller wiring.


## Exact-head CI follow-up — 2026-11-22 02:37 CET

- Current PR #2293 branch head after docs: 3be517af1d83f756852338dbe9b909a748b27f95; tested code/workflow head: e85b7398b1fce84423583abf01e1389507612818; base f0d3c848dfb1d65e282f065233adbe3c9205e439.
- RAW EAR fastpath #44972070097: PASS, 64 tests on Python 3.13 (8.10s) and 3.14 (12.25s); includes 7 new audio-only ingress tests, compile, A5→A4→C3 consumer and privacy scan.
- VAD/libfvad #44972070081: PASS, 8 tests on both Python versions; native libfvad 13/13. Runtime deploy integrity #44972070113: PASS.
- Staged/integrated #44972070090: FAIL at Core-owned local-error pre-rebind semantic pin mismatch (recovery candidate line 313); staged job 19 failed / 231 passed / 10 skipped / 2 errors / 41 subtests, integrated job 1 failed. Same failure on unchanged Boss base in #44969679441. Migration #44972070092 returns PARTIAL; Lab Age/WebView #44972070087 and owner-read #44972070168 fail at stage.
- Boss PR #2288 comment 7072186155 clarified the guard-output generation; Perception corrected its follow-up in #7072323336. Correct sequence: capture guard_semantic_sha and guard_local_error_pin immediately after control_guard.apply_sources(), assert equality, then rebind from the guard-output pin to final_semantic_sha after the Store rebind. Core files untouched.
- LOCAL_LINUX isolated audio_input.py py_compile PASS and pytest 7/7 PASS; exact blobs module 1e9daddcb5dfd8bfb7911090218b4eaf1f103d41 and test b6b1202904efbc417971db6c0d9e3ba0664eef84. Full repo checkout blocked by DNS; no full local Runtime test.
- No audio-only Runtime E2E on current base, no microphone/AudioRecord, no Android TTS, no barge-in, no native speaker model, no Redmi. No release, updater request or device mutation.
- Next: Core resolves the guard-generation pin mismatch; Perception rebases #2293 and adds staged Runtime audio-only E2E, then coordinates Android caller wiring with Core/QA.


## Core pin-generation correction — 2026-11-22

Boss comment #7072186155 clarified that Record-Only control_guard.apply_sources() rewrites both world_semantic_evidence_candidate.py and the local-error consumer pin. The correct expected value for the later Store rebind is therefore the GUARD-OUTPUT local-error pin, not the original base pin. Sequence: capture guard_semantic_sha and guard_local_error_pin immediately after the guard; assert equality; after Store rebind, rebind from guard_local_error_pin to final_semantic_sha; keep the final exact-pin check. Perception corrected its follow-up comment #7072323336 accordingly. No Core-owned file was changed.


## Cross-lane active-perception review — V14-006 / PR #2282 (2026-11-22)

- PR #2282 current head 857d13b4d2aa616cb7e6b154af20ac59e10803be is based on stale #2258 base 9922cf86ecf8801d30a46a1e98817e5c6c1db092, not current Boss #2288. It adds the valuable Store read-vs-revocation FD-under-lock behavior, but is not merge-ready.
- Exact CI: A5 UI lease #44967013094 PASS and runtime deploy integrity #44967013022 PASS; staged/integrated #44967013033 FAIL, Lab Age/WebView #44967012983 FAIL, private owner-read #44967013038 FAIL, two-checkout migration #44967013041 FAIL.
- QA's security finding #6009216985 is still open: validate the stored source hash as exactly 64 lowercase hex characters before using it as a dir_fd-relative path. O_NOFOLLOW only protects the final path component; it does not reject '..' or separators. Add a negative test proving os.open is never called with a path containing separators.
- QA also found the nested stream pin failure: the lifecycle overlay rebinds archive_stream_range to the changed Store, which changes composed stream bytes, but integrated_context_recall still expects the old STREAM_SHA. QA calculated candidate 69267e2772143219b16fbc33118707f413b992e3e71b5715f7744508fd1f406c for the current stale branch, subject to recomputation after rebase.
- Next owner action: after Core's current guard-generation pin chain is green, Boss/QA rebases #2282 onto #2288, adds strict digest-key confinement, recomputes the lifecycle→archive stream→context recall→recovery→stage→deployer chain, and reruns blocking-reader/revocation plus post-revoke negative controls. Perception reviews source/consent provenance; no Android UI provider is inferred.


## Three-regime A4 speaker evidence — 2026-11-22 03:00 CET

- New code in `audio_voice_cues.py`: `_speaker_change_decision()` returns `CONTINUITY_SUPPORTED`, `DEFER`, or `CHANGE_OR_OVERLAP_CANDIDATE`. It requires a measured result, explicit calibration ID, voiced activity and at least two voiced frames before continuity/change can be asserted.
- The decision is attached to the PerceptPacket acoustic metadata and A4 result, and appears early in the bounded C3 admission summary. Silence, unvoiced noise, impulses, uncertain/short windows, warm-up, rejected embeddings and missing calibration explicitly defer. Existing attention gains and authority flags are unchanged; no identity label or action/learning authority is added.
- New tests cover stable, candidate, non-voiced low-similarity, uncalibrated/rejected, short-window and A4/packet integration paths. LOCAL_LINUX standalone helper copy: `py_compile` PASS and 6/6 unit tests PASS; this is not the repository checkout or exact integrated test.
- New research R-064: full 12-page SGM-Diar paper read. The transferable point is explicit deferral plus full-history consolidation; its 0.15/0.45 thresholds are PLDA-z units and were not copied. The paper's full-buffer VBx sleep, speaker prototypes and cross-session memory are NOT implemented here. The study is single-seed on 3 AMI meetings and 5 VoxConverse sessions; causal-strict label stability is poor.
- Current branch includes code commit `5fb790f4aad3825f9f096e814c0ca51354c0f353`, test commit `3472c9183e3fc82f8e0bc12fbb5cb6061da1fdb2`, and the R-064 ledger append. Exact branch head and CI must be read back before any status promotion.
- Full local Aii checkout remains unavailable (GitHub DNS failure); repository compile/integration is therefore CI-only until checkout is available. No Android/Termux/Redmi test, microphone capture, model download, model swap, updater request or deployment.
- Current integration dependency: Boss #2288 is repairing the shared stage/deployer pin chain; exact-head stage/owner-read/audio CI is still running at the last check. Perception's PR #2293 remains stacked on the older Boss base `f0d3c848dfb1d65e282f065233adbe3c9205e439`; rebase only after Boss confirms the exact current head and green integration gates.
- Next executable step: run exact-head RAW EAR workflow, review the A4/C3 packet assertion, then rebase this Perception work onto the verified Boss head and rerun staged/integrated + privacy tests. No user action required.


## Exact branch / coordination readback — 2026-11-22 03:00 CET

- Perception branch head: `552903cbbb92caa5595548c7d016e1c01778d1fe`; PR #2293 remains DRAFT, based on Boss branch `boss/v14-recall-store-pin-rebind-20261122` (its PR base SHA snapshot still reports `f0d3c848dfb1d65e282f065233adbe3c9205e439`).
- Exact blobs: `audio_voice_cues.py` `7ab1a2c9fb34c2a2db2d631067211a0ac54c617c`; `test_audio_speaker_evidence.py` `96f4db5240eb2a43374b8b88f409bea91e1cf2c7`; ledger `ea2b43063da67ae4c9f6d0ee291b0bd929111b6b`. The latest handoff blob is updated separately by this checkpoint commit.
- LOCAL_LINUX helper algorithm: py_compile PASS, 6/6 tests PASS. Full repository local test BLOCKED because no full checkout and GitHub DNS is unavailable. The repository RAW EAR test workflow is not present in the Boss base; only PR privacy and offline-bridge-security checks ran on this head.
- Boss branch exact head readback: `70c04e2a6df21e719bfdf28ab0f3c9f1c6822a39` at 02:08:32 UTC. Its new staged-runtime, staged-audio/arithmetic, A5 UI, owner-read, migration, privacy and related jobs were queued/in progress; no result is claimed for that newer head yet.
- Prior Boss head `bb1d4e8c65f0f271740e12036fe522a9f0564968` had two staged-runtime failures and one staged-audio/arithmetic failure. Root cause from exact logs: the current recovery composition omits `integrated_observer_fair_budget_candidate_20261116.py`; this drops the `minimum_role_slice_s` field and blanket-defers B1/B2 after two C3 prefill failures. The overlay's intended behavior is to retain sequential B1/B2 slices inside the existing pre-answer window, reserve C3 time, and defer only a role whose slice is exhausted. No Perception source was involved.
- Boss PR comment #7072704485 records the exact overlay/composition finding and asks Core to rerun those jobs. Board ticket V14-006 still shows the old Store-blob race as the next step, V14-018 still points to the old #2275 speaker candidate, and `V14_USER_NEXT_ACTION.md` is still timestamped 01:39 CET; Boss owns refreshing those shared files against the new head.
- Next: poll the exact #2288 head; after its stage is green, rebase Perception changes onto that exact SHA, ensure the RAW EAR workflow exists on the integration base, then run Python 3.13/3.14 focused audio + staged/integrated + privacy checks. Do not claim deployment until an authenticated Redmi receipt exists.
