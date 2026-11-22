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
