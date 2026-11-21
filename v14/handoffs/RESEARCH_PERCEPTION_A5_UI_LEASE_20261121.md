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
- The first corrective rerun (run `44941137655`) reached the fixed source-ref readout but still had 2 test failures / 13 passes on both Python 3.13 and 3.14: one assertion still used a top-level source_id, and one generation-revocation test had not persisted an observation before asserting tombstone state. Both test defects are now corrected; the next exact-head rerun is pending. The full local Aii checkout is not mounted and GitHub DNS fails in this worker, so no local repository-level PASS is claimed.
- #2243 is merged at `6bbaa66e4e2454cc2178bd145da95d1e9cf6530f`; this PR is being synchronized to that current base and retargeted from the now-merged research stack to `gpt6/v13-private-remote-bridge-20261111`.
- No OS capture provider, microphone, screenshot, model, permission, updater or Redmi operation was added or changed. REDMI_UNVERIFIED / NOT_RELEASED.


## Second CI diagnosis — 2026-11-21 20:25 CET

- Exact head `cbdd888bb25fc430d7bdef0487f16ed8db5139e8`, run `44941137655`: py_compile PASS; 13 tests PASS / 2 FAIL / 5 subtests on both Python 3.13.18 and 3.14.10.
- The adapter fix itself now returns the cached packet. Remaining failures were test-only: the assertion still expected `packet["source_id"]` rather than `packet["source_ref"]["source_id"]`; the generation-revocation test asserted deletion of a source it had never ingested.
- Updated the assertion and made the test persist the packet before switching the active generation. Final exact-head A5 lease CI passed on both Python versions; broader staged/integrated checks were still pending at final readback.


## Third exact-head attempt — code correction checkpoint

- Code/test correction commit: `bd094187cb7391a5a7e29ecbd94600290496347e`.
- Fixed the remaining two test-only failures from run `44941137655`: source assertion now reads `source_ref.source_id`; the different-generation revocation fixture ingests the event before asserting source tombstoning.
- The GitHub ref update did not yet expose a new Actions run for this code commit. This handoff-only commit is intended to produce a normal push event so the exact corrected code can be re-tested; no pass is assumed.


## Final exact code-bearing SHA and CI — 2026-11-21

- Code-bearing SHA: `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723`; PR #2246 is retargeted to `gpt6/v13-private-remote-bridge-20261111`, with #2243's merged base in ancestry.
- A5 lease push run `44941324466` and PR run `44941328040`: **PASS** on CPython 3.13.18 and 3.14.10; py_compile PASS; 15 tests + 5 subtests PASS on each; privacy scan PASS.
- Generic V13 bridge tests run `44941324373`: PASS. V14 Perception privacy scan run `44941327893`: PASS. Agent-PR integration policy run `44941327955`: PASS.
- Strict safe-additive candidate run `44941327931`: FAIL_BY_POLICY because the PR modifies an existing bridge and shared V14 research/handoff files; the validator only accepts new additive module/test/handoff files. No bypass; manual Boss review remains required.
- Broader staged context/integrated regression run `44941328011` was IN_PROGRESS at final readback. Do not treat this PR as merged or release-ready.
- Local standalone filter test: 4/4 PASS. Full repository local test BLOCKED (no mounted checkout; GitHub DNS unavailable).
- The PR remains synthetic-provider only. No OS observation grant provider, screen capture, actual Android permission, B1/B2/C3 turn hookup or Redmi evidence. `REDMI_UNVERIFIED` / `NOT_RELEASED`.
- No model/weight, updater, permission, app setting or user data changed. No user action is needed for this research/adapter checkpoint.
