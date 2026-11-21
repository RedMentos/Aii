# Research/Perception handoff — A5 UI observation lease — 2026-11-21

## Exact source state

- Working branch: `research-perception/v14-a5-ui-observation-lease-20261121-run11`
- Runtime source: restored byte-for-byte to the base blob `30360f40eb784be5ea975ee85e94a57f0b154164`; no pinned Runtime source edit remains.
- Latest A5 code checkpoint: `01b0c807529d3138e9edb3bc725d04b4db824266` (later ledger/handoff commits are documentation/research-only).
- PR: [#2246](https://github.com/RedMentos/Aii/pull/2246), DRAFT, stacked on #2243 at its original base SHA `543349894b5392582969f06a4485ff9d18e4504d`.
- Parent #2243 has advanced to `3e52c96d7302cdd95896605469ad1fdbe291deee`; #2246 must be synchronized/rebased after #2243 is accepted, then retargeted to the shared integration branch. Do not merge the stale stack directly.
- Release: NOT_RELEASED. No force-push or merge performed.
- Shared V14_WORK_BOARD.json and V14_USER_NEXT_ACTION.md remain Boss-owned; this branch supplies the evidence and next-action text for Boss to incorporate.

## Implemented code

- `v13/code/v13/a5_ui_admission_bridge.py`
  - Strict `v14.a5.ui-observation/1` metadata-only contract.
  - Requires Android ELAPSED_REALTIME, bounded event interval, explicit method/scope/API level, opaque receipt reference, capture session, source ID and PROVISIONAL/FINAL provenance.
  - Rejects raw screenshot/UI text/node tree/package/notification fields and any action/learning authority.
  - Adds a non-copyable, non-serializable, thread-bound UIObservationLease, with current-grant check, linearizable provider guard and persistent revocation subscription.
  - Persists only a content-free A5_UI_EVENT summary and PerceptPacket; calls existing A4 attention and source-bound admission. Provisional packets are stored but not admitted and do not request A4 re-look.
- `A5UIRuntimeAdapter` wraps the existing Runtime object and uses its real Store and A4 controller without changing the pinned Runtime source. It provides lease, ingest, FINAL-only context, revoke and explicit close operations. Core must instantiate it in the active-turn path and call adapter.close() before Store shutdown.
- `v13/code/tests/test_a5_ui_observation_lease.py` adds a repository-level test using the actual Runtime/Store/Attention classes and a synthetic OS provider.
- `v14/V14_RESEARCH_LEDGER.md` contains R-038 (Android UI/A5 permissions), R-039 (MobileVLM V2 candidate), and new R-042 (SmolVLM-256M candidate).

## Tests and evidence

- LOCAL_LINUX / CPython 3.13.5: isolated bridge py_compile PASS.
- LOCAL_LINUX / CPython 3.13.5: isolated harness 14/14 PASS with a synthetic SQLite Store and fake A4/provider. Covered source/generation/receipt/thread binding, provisional exclusion, Android API scope rules, non-reentrant revocation race, packet/source/cache/blob cleanup, and raw-field/authority rejection.
- The isolated harness is not the full Aii repository test suite. The added repository-level unittest has not yet run locally because no complete checkout is mounted in this execution environment.
- Exact PR-head CI on `ad0d6a3b1f4935b22677c6f9c521ec97e099deec`, run `44940487917`: `py_compile` PASS on Python 3.13.18/3.14.10; A5 UI lease tests FAIL 3 / PASS 12 / 5 subtests on both versions; staged-runtime PASS; integrated-regression was IN_PROGRESS at the last read. The failing tests and adapter source-ref bug are recorded in R-043. Corrective rerun is pending.
- Redmi/Android: REDMI_UNVERIFIED. No connected authorized phone, OS capture provider, AccessibilityService, NotificationListenerService or MediaProjection session was exercised.

## Actual consumer effect and limits

A5UIRuntimeAdapter consumes the existing Runtime object: it persists a metadata-only PerceptPacket, drives the existing A4 scorer and returns bounded source-bound admission for an active turn. Its process cache exposes FINAL packets only and adapter revocation removes the source and dependent data.

This does not yet make the installed app observe or understand the screen. There is no authenticated OS-issued observe_ui provider, no screenshot decoding/visual model, and no automatic _turn queue hookup or B1/B2/C3 delivery. Core must call the adapter from the active turn and close it before Store shutdown; this Perception adapter is not a completed Android feature. A5 UI remains SHADOW / WIRED_SYNTHETIC, not ANDROID_VERIFIED.

## Research and permissions

- Android AccessibilityService is restricted to genuine disability-assistance use for this contract; generic accessibility harvesting is rejected. Android platform retrieval is capability-gated and user-enabled.
- MediaProjection is session-consented; Android 13/API 33 is full-display scope, while app-window sharing requires API 34. Redmi Android 13 must not be described as app-only projection.
- NotificationListenerService is notification-scoped and separately user-enabled.
- App intents/content providers are preferred when the target app provides them.
- No third-party OSS, model, weights, dependencies, user data, app permission, model selection or installed setting changed.

## Visual teacher research — R-039 MobileVLM V2

MobileVLM V2 1.7B is a plausible on-demand A5 visual teacher, not a default or always-on model. The full main sections of arXiv:2402.03766v1 (2024-02-06 preprint) were reviewed. It uses CLIP ViT-L/14 at 336×336, MobileLLaMA-1.4B-Chat and LDPv2, reducing 576 visual tokens to 144. The paper reports 51.63 tok/s on Jetson Orin with a 4-bit LLM; this is not Android evidence.

The current llama.cpp MobileVLM guide (blob `6c17dbf902eafc6d262d6faa846ff5999fd6d8ab`) documents an Android aarch64 build and a Snapdragon 778G V2 run: 20.61 s image encoding, 12.83 output tok/s, 44.41 s total for 377 tokens using release-2005b and F16 mmproj. The Redmi Note 10 Pro / Snapdragon 732G remains unmeasured and may be slower. A community Q4_K pair is about 961 MB on disk (792 MB LLM + 169 MB mmproj); this is not a RAM estimate.

License caution: code is Apache-2.0; model cards label V2 and MobileLLaMA Apache-2.0; CLIP is labeled MIT; the paper uses ShareGPT4V-PT, whose dataset card is CC-BY-NC-4.0. Do not treat the entire trained artifact as cleared for commercial redistribution without provenance review. No download, conversion, build or swap was attempted.

## Additional visual teacher research — R-042 SmolVLM-256M

The full paper **SmolVLM: Redefining small and efficient multimodal models**, arXiv:2504.05299v1 (2025-04-07 preprint), was reviewed. The 256M model combines a 93M SigLIP-B/16 encoder with SmolLM2-135M. The paper reports 0.8 GB GPU VRAM at batch 1; OCRBench 52.6%, TextVQA 50.2%, DocVQA 58.3%. The 500M variant is stronger (61.0/60.2/70.5) but reports 1.2 GB GPU VRAM. Paper throughput tests use A100/L4 GPUs; the smartphone demo is not a Redmi 732G benchmark. Smaller variants struggle beyond 8k context, and aggressive visual compression can hurt fine OCR/localization.

- Original checkpoint revision: `d039ab0d4b9311b617e8ffec1d06c8464364aeb3`; model card labels Apache-2.0 and lists Apache-2.0 base-model cards for SmolLM2-135M-Instruct and SigLIP-B/16.
- GGUF conversion revision: `b9e4379657e1450d04d02eec8e345667265b0a00`; model card labels Apache-2.0. Q8 model+mmproj: 175+104=279 MB on disk; F16 pair: 328+190=518 MB. This is storage size, not RAM/PSS.
- Official llama.cpp multimodal docs list SmolVLM-256M and use libmtmd; Android docs document building/running llama.cpp CLI from Termux. The exact combined Android model+mmproj path is not yet built or tested.
- The model card lists The Cauldron and Docmatix; their full dataset-license/provenance terms were not audited in this pass. No weights/data were downloaded.

R-042 is a candidate only: use as an A4-triggered visual teacher, not an always-on body or action executor. It does not establish reliable UI coordinate/tap grounding. The next benchmark, if approved, should compare 256M Q8 and 500M Q8 on Redmi with actual load/peak PSS, image-resolution sweeps, TTFT/output speed, thermal/battery and OCR/UI-task quality. Use only synthetic or explicitly consented local screen fixtures; negative controls include no-image, blurred, shuffled and stale-receipt inputs. No download or model swap was attempted.

## Next executable ownership

1. Core: provide a trusted Android observe_ui receipt provider and call Runtime ingress from the active-turn path; hold the lease across all downstream source reads and C3 generation.
2. QA: adversarially test revocation through capture → admission → A4 → B1/B2/C3/cache, stale receipt/session, Runtime shutdown and provider failure.
3. Research/Perception: after Core's provider exists, add actual screen/UI feature packets and compare API-first event feeds against permitted visual capture; keep raw UI content out of logs and public artifacts. A SmolVLM experiment download is separate and requires explicit user consent first.
4. Boss: review the adapter/contract, update the shared board and V14_USER_NEXT_ACTION.md, and retarget #2246 to the integration branch after #2243 is accepted.

No user action is needed now. Current installed Redmi SHA/updater status was not queried in this run; no update request or deployment was attempted.


## Exact-head regression repair — 2026-11-21 20:25 CET

- Reviewed failing CI logs from run `44940487917` on exact code head `ad0d6a3b1f4935b22677c6f9c521ec97e099deec`.
- Fixed the actual context-readout defect: `PerceptPacket` has nested `source_ref.source_id`, not a top-level `source_id`; the adapter now checks nested source identity plus exact event and generation.
- Fixed two test defects without weakening the API: the generation test now binds `grant`; tests pass the required live lease, keep provisional context empty, and assert lease-free reads fail closed. Added wrong-source and wrong-generation cache entries as negative controls.
- The first corrective rerun (run `44941137655`) reached the fixed source-ref readout but still had 2 test failures / 13 passes on both Python 3.13 and 3.14: one assertion still used a top-level source_id, and one generation-revocation test had not persisted an observation before asserting tombstone state. Both test defects are now corrected; the final exact A5 lease runs passed at code-bearing SHA `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723` on Python 3.13 and 3.14. The full local Aii checkout is not mounted and GitHub DNS fails in this worker, so no local repository-level PASS is claimed.
- #2243 is merged at `6bbaa66e4e2454cc2178bd145da95d1e9cf6530f`; PR #2246 is now based directly on `gpt6/v13-private-remote-bridge-20261111`.
- No OS capture provider, microphone, screenshot, model, permission, updater or Redmi operation was added or changed. REDMI_UNVERIFIED / NOT_RELEASED.


## Second CI diagnosis — 2026-11-21 20:25 CET

- Exact head `cbdd888bb25fc430d7bdef0487f16ed8db5139e8`, run `44941137655`: py_compile PASS; 13 tests PASS / 2 FAIL / 5 subtests on both Python 3.13.18 and 3.14.10.
- The adapter fix itself now returns the cached packet. Remaining failures were test-only: the assertion still expected `packet["source_id"]` rather than `packet["source_ref"]["source_id"]`; the generation-revocation test asserted deletion of a source it had never ingested.
- Updated the assertion and made the test persist the packet before switching the active generation. Final exact-head A5 lease CI passed on both Python versions; broader staged/integrated checks were still pending at final readback.


## Third exact-head attempt — code correction checkpoint

- Code/test correction commit: `bd094187cb7391a5a7e29ecbd94600290496347e`.
- Fixed the remaining two test-only failures from run `44941137655`: source assertion now reads `source_ref.source_id`; the different-generation revocation fixture ingests the event before asserting source tombstoning.
- The final A5 push and PR workflows subsequently ran on code-bearing SHA `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723` and passed on both Python versions; see the final evidence section below.


## Final exact code-bearing SHA and CI — 2026-11-21

- Code-bearing SHA: `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723`; PR #2246 is retargeted to `gpt6/v13-private-remote-bridge-20261111`, with #2243's merged base in ancestry.
- A5 lease push run `44941324466` and PR run `44941328040`: **PASS** on CPython 3.13.18 and 3.14.10; py_compile PASS; 15 tests + 5 subtests PASS on each; privacy scan PASS.
- Generic V13 bridge tests run `44941324373`: PASS. V14 Perception privacy scan run `44941327893`: PASS. Agent-PR integration policy run `44941327955`: PASS.
- Strict safe-additive candidate run `44941327931`: FAIL_BY_POLICY because the PR modifies an existing bridge and shared V14 research/handoff files; the validator only accepts new additive module/test/handoff files. No bypass; manual Boss review remains required.
- Broader staged context/integrated regression run `44941328011` completed **PASS**: staged-runtime 251 passed / 10 skipped / 47 subtests; integrated-regression 424 passed / 3 skipped / 58 subtests (6 warnings). This is CI staged/synthetic evidence only; do not treat the PR as merged or Redmi-verified.
- Local standalone filter test: 4/4 PASS. Full repository local test BLOCKED (no mounted checkout; GitHub DNS unavailable).
- The PR remains synthetic-provider only. No OS observation grant provider, screen capture, actual Android permission, B1/B2/C3 turn hookup or Redmi evidence. `REDMI_UNVERIFIED` / `NOT_RELEASED`.
- No model/weight, updater, permission, app setting or user data changed. No user action is needed for this research/adapter checkpoint.


## Cross-lane preservation warning — Core #2242

- Current Core PR #2242 head `edefe004735513bfa531984fb2662da5adb6a997` is based on the same declared release SHA `6bbaa66e4e2454cc2178bd145da95d1e9cf6530f`, but its diff deletes the merged #2243 experiment folder, R-037 from the research ledger, the Perception handoff, and the dedicated latent-cache model-lab workflow job.
- This is an accidental ownership/ancestry conflict with already-merged research, not a requested removal. A blocking comment was posted on Core #2242 and on whole-system issue #1984. Research/Perception did not edit Core-owned files; preserve these merged artifacts before any Core merge.


## New A5 visual grounding research — 2026-11-21

- Added R-044 to the research ledger: GoClick (arXiv:2604.23941) is a promising two-stage GUI grounding research lead, but only its abstract and maintained MIT repo/model card were reviewed. The 0.3B F32 GoClick-Base uses Florence-2-large, Transformers `trust_remote_code`, PyTorch and timm; no GGUF/ARM64/Android path or device benchmark was found. Dataset license/provenance remains unaudited. It is not a Redmi download candidate today.
- MobileExplorer (arXiv:2605.26546) abstract proposes parallel read-only exploration and two-level rollback; full paper/code/license/device conditions were not verified. Full-text review now reports 50.86% (59/116) vs 46.55% success, 9.24 vs 10.93 steps (15.5% fewer in the table), and 185.82 s average task time (15.9% below M3A). The conclusion's ~23% fewer-step statement conflicts with the table; it is not a 23% latency result. Possible future experiment: bounded read-only UI information gathering with source-bound traces and state alignment; no speculative tap authority.
- Official Android docs confirm MediaProjection's user-grant flow and API-34+ foreground-service requirements. No screen capture or permission was attempted. Links and limitations are in R-044.


## Broader integration CI completed — 2026-11-21

- Run `44941328011` on code-bearing SHA `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723`: **PASS**.
- Staged Runtime: 251 passed, 10 skipped, 47 subtests.
- Integrated regression: 424 passed, 3 skipped, 58 subtests (6 warnings).
- Together with A5 UI lease 15/15 + 5 subtests on Python 3.13/3.14, this validates the CI-staged integration surface at that SHA. It is not a real Android provider or a Redmi test.
- Strict additive gate remains FAIL_BY_POLICY; Boss review and preservation of #2243 artifacts in Core #2242 remain necessary before merge.


## 2026-11-21 — shared content-addressed blob race fix

QA PR #2250 exposed a real integrity race: A5 source revocation could tombstone one source, release the Store mutex, and then unlink a shared content-addressed blob after a second producer had reused it and committed another live source row.

The Perception branch now serializes both sides with the Store's existing re-entrant mutex:
- A5 publication holds the mutex across blob existence/write, source + PerceptPacket transaction, and failure cleanup.
- A5 revocation holds the same mutex across tombstone, live-reference count, and final blob unlink.
- Generic `Store.source()` now holds that mutex across its blob existence/write and source-row transaction, so it cannot race the A5 revocation path.

A new CI regression exercises the real `Store.source()` producer against the real A5 revocation function on separate threads. The QA-owned #2250 A5-to-A5 regression must also move its second producer to a separate thread: a correctly serialized producer blocks while revocation owns the mutex, so a synchronous producer call would deadlock the test until its timeout. Do not weaken that regression.

**Local evidence:** a LOCAL_LINUX isolated reproduction using the exact observed lock/transaction ordering failed before the fix with a live second SourceRef plus `FileNotFoundError`, then passed after the fix with the producer blocked until unlink completed and the new source readable. This is a focused copied-code concurrency harness, not a full Aii checkout test.

**CI status:** pending exact-head CPython 3.13/3.14 run. The full repository checkout is not mounted and GitHub DNS resolution fails in this worker. No full local Aii suite was run.

**Boundary:** this remains a synthetic A5 metadata contract. No Android UI provider, AccessibilityService, MediaProjection, screenshot capture, action executor, microphone, or Redmi test is present. `REDMI_UNVERIFIED` / `NOT_RELEASED`.


## Exact-head CI readback and pin dependency — 2026-11-21

- A5 UI lease + shared-blob workflow run **44945017268**: PASS on CPython 3.13 and 3.14. Each matrix job: **16 passed / 5 subtests passed**; compile step passed.
- Public privacy scan run **44945017328**: PASS.
- Safe-additive candidate run **44945017280**: FAIL_BY_POLICY because this PR intentionally changes existing A5 and Store modules. This is a protected-file review gate; no bypass requested.
- Staged-runtime run **44945017337**: FAIL; integrated-regression same run: **19 failed, 230 passed, 10 skipped, 2 errors, 41 subtests passed**. All cascading stage failures identify the stale exact-source pin for v13/store.py in v13/code/scripts/integrated_online_world_candidate_20261110.py, not an A5 race assertion.
- Old pinned SHA-256: fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980. New exact v13/code/v13/store.py SHA-256 on this branch: 40a387e24f8c4d9533bde484c1c82c1dd700517fa652469b4eea7b8b21a471bb. The hash implementation was checked against the standard SHA-256("abc") vector and the old pinned Store file hash. Core owns the integrated stage candidate/pin chain; this dependency was reported on Core #2254 rather than editing Core-owned files here.
- Local copied-code harness remains 20/20 original A5 race failures vs 20/20 patched passes, and 10/10 original generic Store.source failures vs 10/10 patched passes. Full local repository checkout remains BLOCKED.
- This branch remains DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. Boss/Core must update and verify the staged source pin before merge; safe-additive review is also still required.


## 2026-11-21 — RAW_EAR / WebRTC VAD benchmark note (R-046)

The exact RAW_EAR extractor logic was copied from the current shared source and exercised locally on Python 3.13.5 x86_64 with deterministic synthetic PCM16 controls. A one-second window cost median 131.30 ms (p95 135.89 ms); a 40-ms window cost 2.68 ms and a 100-ms window 10.58 ms. The WebRTC VAD baseline (mode 2, 50 × 20-ms frames) took 0.094 ms median, but it emits only binary activity, not F0/prosody.

The negative controls show why the signals must remain separate: RAW_EAR classified pure tone as VOICED, broadband noise as UNVOICED_NOISE and impulse bursts as IMPULSIVE; WebRTC VAD treated loud synthetic noise and impulses as speech-like activity. These are synthetic controls, not speech accuracy. No ARM or Redmi timing is inferred.

OSS review: webrtcvad-wheels 2.0.14.post1 has an MIT wrapper and bundled WebRTC BSD-style C license, but its Linux ARM64 wheels are glibc/musl rather than Android Bionic. libfvad is BSD-3-Clause C, but its open noise false-positive issue and old release history require caution. The current optional Silero ONNX path was not run and no weights were downloaded.

Next: measure incremental 40–100-ms RAW_EAR on Redmi with explicit test-audio consent, then compare a native/vectorized autocorrelation backend while retaining separate VAD and non-speech cues. This is a local synthetic benchmark only, not a product runtime or phone result.


## 2026-11-21 — RAW_EAR optional NumPy backend (R-047, PR #2256)

The current pure-Python RAW_EAR pitch autocorrelation measured 131.30 ms median / 135.89 ms p95 per one-second 16-kHz synthetic window on LOCAL_LINUX Python 3.13.5 x86_64. A hybrid NumPy implementation that vectorizes only normalized autocorrelation measured 6.23 ms median / 8.37 ms p95 (~21× faster) and matched the Python output on 100/100 random synthetic windows across 8–48 kHz and 40-ms to 1-s durations. tracemalloc peak increased by ~12 KB while NumPy was already imported; cold import and process RSS were not measured.

PR #2256 exposes this as an explicit opt-in backend on extract_voice_cues and consume_pcm16_voice_window. Default remains pure Python; Core must not enable the NumPy path on the installed phone until cold import/RSS/latency and full-duplex behavior are measured on Redmi. No model, microphone permission or user audio was used.


## Research/Perception run 11 — 2026-11-21T20:36:33.179Z

### A5 shared-blob test hardening

- QA requested that the generic `Store.source()` race test stop relying on a 50-ms scheduler window. Applied a tracking wrapper around the actual Store RLock and an observed `Path.exists` boundary. The test now proves that the producer thread started, attempted the same lock while revocation was paused at unlink, did not reach blob existence or complete before release, then resumed and published a readable SourceRef.
- Code/test commit: `ebcbca01d539f2b1a3a5eef8ac3c19e4d80e23a4`; test blob readback `662f9f698ae258a7545b1d5af0e3d0e3e7155e18`. Documentation-only descendants: board `1a369dc1fbab5fca41325c22568aa73f69364e0b`, next-action `538e93843f146df4652eb0ec8b2b58837c80802c`.
- A5 workflow `44946951711` is still running on Python 3.13; its Python 3.14 job was cancelled when the run was superseded. It must be re-run after the 3.13 job completes. Public privacy scan `44946951817` PASS. Staged/integrated workflows fail on the known Core pin: expected old Store SHA-256 `fe66f925...`, actual new Store source `40a387e24f8c4d9533bde484c1c82c1dd700517fa652469b4eea7b8b21a471bb`. This is a composition blocker; do not patch Core-owned builder here.
- Core #2254 has been given the exact semantic requirement: its lifecycle builder must preserve the outer `with self.mutex:` around blob verification/write and nested `with self.tx()`, then refresh the full downstream pin chain. A raw hash-only update would reintroduce the race.

### RAW EAR opt-in NumPy backend

- PR #2256 exact code head `63b5410769b872ddb64e002ab1c764e9e90966af`; benchmark direct-invocation path fix is in that commit. Focused workflow `44946779051` PASS on CPython 3.13 and 3.14 (compile, 42 tests each, deterministic synthetic benchmark, privacy). Prosody, consent-revocation and WebRTC/libfvad workflows also PASS. The staged/integrated workflow remained in progress at last readback; safe-additive validator remains FAIL_BY_POLICY.
- Local x86 synthetic comparison already recorded in R-047: 131.30 ms → 6.23 ms median per 1-s 16-kHz window (~21×), 100/100 output parity, +12,038 bytes tracemalloc while NumPy was already imported. No cold import, process RSS, real speech accuracy, ARM or Redmi measurement.
- Official Termux package recipe checked: NumPy 2.5.5, BSD-3-Clause, Android aarch64 build path, dependencies libc++/libopenblas/python. This supports feasibility but does not prove installation on the user's device. No package installed; Python remains default and NumPy is explicit opt-in.

### Status / next

- `NOT_RELEASED`; `REDMI_UNVERIFIED`; no device action, updater request, model/weight change, permission or user-data change.
- Core: compose #2255's Store lock into the staged lifecycle builder and recompute pins. QA: rebase #2250 after composition and retain the deterministic separate-thread A5-to-A5 race. Boss: review protected-file/safe-additive policy and PR ownership. NumPy: leave opt-in until authorized Termux cold-import/RSS/short-window/full-duplex measurements.
