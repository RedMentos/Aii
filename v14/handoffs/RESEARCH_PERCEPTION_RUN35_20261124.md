# Research & Perception — Run 35 — 2026-11-24

**Started:** 2026-11-24 06:47:24 Europe/Berlin  
**Checkpoint recorded:** 24/11/2026, 07:05:32 Europe/Berlin  
**Completion:** UNKNOWN (the run continued after this checkpoint)  
**Repository:** RedMentos/Aii  
**Working branch:** `research-perception/v14-audio-duplex-bridge-20261123-run21`  
**Code commit:** `825ecfbd1a530fdba3ba830b0087cd35933ef464`  
**Release-development base:** `8d93236c753f0194224c19edc7411d8d7082b1d6`  
**PRs:** #2448 OPEN/DRAFT/NOT_RELEASED; #2463 OPEN/DRAFT/NOT_RELEASED

## 1. Implemented code

Commit `825ecfbd1a530fdba3ba830b0087cd35933ef464` changes:

- `v13/code/v13/audio_voice_cues.py`: A4's returned packet now explicitly contains `identity_authority=False` alongside `learning_authority=False` and `action_authority=False`. This fixes the exact current-head regression expecting that identity is not authorized by speaker-change evidence.
- `.github/workflows/v14-raw-ear-vad-comparison.yml`: `V14_EXPECTED_RAW_EAR_V3_BLOB` now pins the exact new Git blob `5be9e12fd2a51dfccc1d58c8aa784695cc7b0ac3`, instead of the stale pre-edit blob. GitHub readback matched both new blobs.

No model, weight, data, permission or Android configuration was changed.

## 2. Test evidence

### LOCAL_LINUX

- Full Aii checkout and full local suite: **BLOCKED / NOT_RUN**. No repository checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` fails because github.com DNS cannot resolve.
- Isolated local A4 authority-contract reproduction: **PASS** (dictionary syntax and assertions that identity, learning and action authority are false). This is not a full module test or repository suite.

### GitHub Actions — exact commit 825ecfbd

| Run | Result |
|---|---|
| 45336790279 audio duplex | **PASS** — 189/189 on Python 3.13 and 189/189 on Python 3.14 |
| 45336790251 RAW EAR optional NumPy/speaker path | **PASS** — 128/128 on Python 3.13 and 3.14 |
| 45336790325 WebRTC/libfvad comparison | **PASS** — 72/72 on Python 3.13 and 3.14 |
| 45336790459 prosody-to-attention | **PASS** — 72/72 on Python 3.11 and 3.13 |
| 45336790416 consent-revocation QA | **PASS** |
| 45336790269 public privacy scan | **PASS** |
| 45336790259 runtime deployment integrity | **PASS** |
| 45336790400 staged/integrated | **FAIL** — Core-owned audio source pin still rejects `v13/audio_voice_cues.py`; 16 failed, 237 passed, 10 skipped, 2 errors, 47 subtests. The migration subtests also return PARTIAL instead of UPDATED. |
| 45336790334 Core same-turn | **FAIL** on Python 3.13 and 3.14 at the same Core-owned stale audio source pin. |

The Perception-owned comparator pin is fixed and its exact-head workflow passes. The remaining staged/same-turn failure is not in the Perception workflow: Core's `integrated_audio_context_candidate_20261121.py` still expects an older audio blob. Perception did not edit the Core composer or weaken its source check.

### Cross-agent handoff

Comment **7123452298** was posted to Core PR #2462 with exact current blobs:

- audio voice cues: `5be9e12fd2a51dfccc1d58c8aa784695cc7b0ac3`
- audio speaker evidence: `14a6d8d79d361e6c89c3770d372a3f9824f13afb`
- audio temporal evidence: `e258f5dfecbf79d6f1a9d3adbfaf60631bb9d140`
- vision source: `vision.py` = `5b7c92f0ffc1e89c4d71c0a3ab819e18722a23b2`; source-lineage = `8958f1297378653ec1837a215f84a41b14966db9`; UI frame ingress = `01251275def732ef7df1c862f7ee22e9926112a4`.

Core/Integrator must recompose the audio pin set on the combined candidate. Core/JEPA must add a reviewed `vision.py` source-lifecycle mapping and source-forget regression. PR #2463's focused vision source-lineage (29/29) and RAW EYE provider-frame ingress (39/39) pass on Python 3.13/3.14, but staged/integrated still rejects `vision.py`; no Perception bypass was made.

## 3. Research R-128

Two complete primary papers were read and added to `v14/V14_RESEARCH_LEDGER.md`:

1. Patamia et al., *Leveraging Dual-Process Theory for Multimodal Multiparty Turn-Taking Prediction*, arXiv:2611.19484v1 (2026-11-14). Full 13-page PDF. It separates high-recall candidate discovery, selective verification and event localisation. Its VoxConverse Task C F1 is 0.552 at ±0.5 s, but the executed pipeline uses offline-precomputed diarization/ASR/embeddings and bounded look-ahead; its component RTF is not end-to-end streaming. Multi-TPC seven-group comparisons do not survive Holm correction. The derived VoxConverse labels are only 75.3% fine-grained / 86.0% coarse transfer agreement in a 300-clip human audit. The paper cites Ruddy202/DualTurn, but that exact repository/license could not be verified.
2. Mathur & Manocha, *MultiPartyTurnBench: Benchmarking Floor Control in Multi-Party Spoken Dialogue*, arXiv:2610.20172v1 (2026-10-14). Full 31-page PDF and official benchmark docs. EOT and successful INT are distinct: strong EOT recall does not imply selective interruption. The paper's full-duplex agent study reports 86.1–95.8% turn-entry balanced accuracy but only 46.9–54.7% STOP/yield balanced accuracy. Provider-VAD cancellation can masquerade as model-driven yielding. Benchmark code MIT; dataset CC BY 4.0, gated, about 2.46 GB. No code, data or weights were downloaded.

**Implementation implication:** speaker change and voice onset are candidate evidence, not proof of floor transfer. V14 should separately measure candidate discovery, EOT/hold, successful INT/floor acquisition and event localisation. Current explicit `duplex_mode=interrupt` is a provider-voice-onset barge-in option, not a learned selective-yield policy. The new research is recorded as a testable next experiment, not implemented or promoted to decision authority.

## 4. User effect, release and device status

- The A4 authority field is now present in the PR candidate; it does not become a user-visible product behavior until integrated and released.
- PR #2448: OPEN/DRAFT/NOT_RELEASED. PR #2463: OPEN/DRAFT/NOT_RELEASED.
- Last authenticated phone receipt #832 (2026-11-23 17:37:47 UTC) reported base `8d93236` installed and auto-update enabled. It predates these open PR heads; no installation receipt for `825ecfbd` or `b73ec8a7` exists.
- **TERMUX/REDMI: REDMI_UNVERIFIED.** No handset was connected; no microphone/AudioRecord, MediaProjection, native speaker model, Android RAM/latency or UI-control test occurred.
- No UPDATE_REQUEST, manual Termux command, model download/swap, permission change or data mutation was sent.

## 5. Next executable steps

1. Core/Integrator rebinds the exact audio source blobs and runs the combined staged/integrated/same-turn matrix.
2. Core/JEPA adds the `vision.py` lifecycle/source-forget mapping and tests.
3. After combined CI is green, Boss/QA may use the existing authorized updater and obtain a separate PIPELINE_STATUS receipt. GitHub push is not deployment.
4. Perception proceeds with source/session-disjoint A4 outcome/retention and model-bound speaker embedding calibration, then a causal EOT/INT event benchmark with backchannel/hold/laughter/overlap hard negatives.

**User action:** none.


## Addendum — correct source-lifecycle integration owner

A changed-file ownership recheck shows that Boss/Integrator PR #2443, not Core fair-budget PR #2462, owns the stale `integrated_audio_context_candidate_20261121.py` and `source_lifecycle_lock_integration_candidate.py` composers. Current #2443 head at review: `cdf6b64067ac426ba32194100d3764f6e74c105f`. Current exact Perception audio blobs and SHA-256 plus current #2463 `vision.py` blob/SHA-256 are in #2443 comment 7123664991. The current #2443 composer branch still pins older Perception bytes. Perception did not edit Boss-owned files; it handed the exact hashes to the owner and requested a strict bottom-up recompose with #2448 and #2463 stacked/rebased. The earlier #2462 comment 7123452298 remains an FYI, not the primary owner handoff.
