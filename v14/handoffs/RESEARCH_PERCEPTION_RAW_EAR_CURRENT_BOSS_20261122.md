# Research & Perception handoff — current-Boss RAW EAR rebase
Date: 2026-11-22 05:00 CET
Owner: Research & Perception

## Branch and code
- Branch: `research-perception/v14-raw-ear-currentboss-20261122-run11`
- Code commit: `cfccb91ac9a3ff49f8aae259f92ad8118eaf19c5`
- Base: Boss integration branch `boss/v14-recall-store-pin-rebind-20261122` at `6e6f15322c9fa1931dcf733105d2a32d5372edeb` (docs-only descendant; code-bearing parent `483ef6ddc7140bf76f197d538ec973df42dd95e0`).
- New code paths: caller-supplied audio-only PCM16 ingress; bounded source/generation-bound speaker-similarity diagnostics; A5/A4/C3 audio context in the staged Runtime; optional NumPy pitch backend remains OFF by default.

## Consumer and safety contract
- `audio_input.submit_audio_only(runtime, audio_window)` submits a fixed no-transcript marker and the original caller-supplied window to the staged `Runtime.submit(..., audio_window=...)` contract.
- Source ID, opaque consent receipt, preflight check, lease guard, two-phase revocation subscription and PROVISIONAL/FINAL provenance are mandatory. This adapter does not capture a microphone, transcribe, persist PCM, download models or learn weights.
- Speaker embeddings are caller-supplied and process-local. Uncalibrated thresholds produce raw cosine diagnostics only; A4/C3 remain DEFER. No speaker identity, attention gain, action authority or cross-recording link.

## Exact source-pin readback
- `audio_voice_cues.py` blob: `596d14487b9f2b28609eea79fb8b1b39f8da009c`
- `audio_speaker_evidence.py` blob: `37aa9c392bbb68d60ccff9749c75b41b8783c539`
- integrated audio builder blob: `f79f5c2e36b396fbea2d5d9177729f72c0250c3d`
- recovery wrapper SHA-256: `0ad300e467ecaa0befca6749a1ad9995fe9a715dc49c3556dd0462212a28ca6e`
- stage builder SHA-256: `c24fae1a4cb9b1bc36c3e6064afd15cff432e65833940b46796a41ad697d0623`
- runtime deployer `STAGER_SHA256`: matches the stage builder SHA above.
- VAD comparison workflow expected voice-cue Git blob: matches `596d...`.

## Tests and evidence
- **GitHub source/blob readback:** PASS for the exact files and pin chain above.
- **LOCAL_LINUX full repository suite:** BLOCKED. Environment CPython 3.13.5; no Aii checkout mounted; `git ls-remote https://github.com/RedMentos/Aii.git` fails because github.com DNS cannot resolve.
- **Scratch tests from prior Perception branch:** historical only; not claimed for this new commit. Exact-head CI is pending until PR creation.
- **Native / Android / Redmi:** NOT TESTED. No phone receipt, microphone capture, native speaker encoder, B1/B2/C3 native model execution, TTFT/RSS or install proof.

## Research and decisions
- R-058–R-069 carry the reviewed FASTDIAR, ReDimNet2, eDIAR, TTS/full-duplex, surprise-gated memory, NumPy benchmark, calibration, llama.cpp representation and PACT-Check findings.
- PACT-Check is the relevant cross-organ safeguard: task gains are not communication evidence without dummy, irrelevant, self-communication and receiver-only controls. PLatour is a Linux/CUDA research stack; reuse the evaluation protocol, not the runtime.
- No model, weight, dependency, permission, updater, device state or user data changed.

## Next executable action
Wait for this exact PR head's Python 3.13/3.14 audio, VAD, staged/integrated, migration, owner-read, privacy and deployer checks; fix only exact reproduced failures. Boss/QA then review integration. Keep microphone, model, speaker decision and learning gates OFF until separate evidence and authorization.

Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. User action: none.


## Exact-head CI checkpoint (2026-11-22T04:21:17.255Z)

- Tested code-bearing commit: `5010ba083f0480d4e2249a4246cb13d453827f93`; PR #2304; all **15/15** check-runs SUCCESS.
- RAW EAR fastpath: `py_compile` plus 73 tests on Python 3.13.18 and 73 tests on Python 3.14.10. CI benchmark only: Python autocorrelation median 115.48 ms (3.13) / 189.67 ms (3.14); NumPy median 5.38/8.99 ms; speaker-evidence consumer median 0.617/1.042 ms. NumPy remains opt-in; these are hosted-runner figures, not Redmi measurements.
- VAD comparison: 8 tests PASS on each Python version; exact workflow source hash equals `596d14487b9f2b28609eea79fb8b1b39f8da009c`.
- Staged runtime: 252 passed, 10 skipped, 47 subtests; staged ContextOS source recall 15 passed; arithmetic/output policy 39 passed and 17 subtests. Integrated regression: 424 passed, 3 skipped, 58 subtests. Composed C4/C3 consumer: 10 focused tests PASS on each Python version. CI also passed runtime-deployment-integrity, two-checkout migration, owner-read, lab-age E2E, and offline bridge security. These are CI/synthetic checks, not Android proof.
- Current Boss base head `6e6f15322c9fa1931dcf733105d2a32d5372edeb`: 29 success, 0 failure, 1 skipped. The code-bearing parent `483ef6ddc7140bf76f197d538ec973df42dd95e0`: 26 success, 0 failure, 1 skipped.
- Local full suite remains BLOCKED because the runner has no repository checkout and GitHub DNS cannot resolve. No current local test PASS is claimed.

## Private device status
- Private V13OBS issue #115 last receipt updated 2026-11-18: auto-update enabled and dashboard says UPDATED, but runtime is ERROR and last result PARTIAL; the observation is stale.
- Private V13READ issue #461 remains open with no device_status comment/receipt. Status: `NO_LIVE_RECEIPT`; current install, updater operation and runtime response are not verified. No update request or device action was sent.

## R-071 model research
- FASTDIAR (arXiv:2610.02941, 2026-10-02): 80-ms embeddings, 2-s past context, 960-ms delay; code MIT, checkpoint license unresolved; desktop CPU evidence only.
- Nemotron 3 Diarization (arXiv:2611.12246, 2026-11-09): 99M params, 8 speakers, 0.32–1.04-s buffer, OpenMDW-1.1 weights; GPU results only; teacher reference, not Redmi candidate.
- eDIAR (arXiv:2611.18529, 2026-11-13): Apache-2.0 code/no weights, 99.2M+6.6M models, 90-s bounded clustering, 10-s revision, 1.9–3.8 GiB CPU RSS, English-only/no far-field. Algorithm reference only; no cross-recording identity linking in V14 without explicit consent.
- No model or weights were downloaded, selected, or swapped.

Status remains DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. Next: Boss/QA review and separate consent-gated Android AudioRecord provider, then real Redmi measurements.


## Low-gain RAW EAR correction — 2026-11-22

- PR #2304 code-bearing head: e28982337ca714fb4d14a3a972f3beafacc248c4.
- Defect: a 140 Hz, 100-count PCM16 tone produced whole-window RMS 0.002144 (<0.003), voiced_fraction 1.0 and confidence 0.992, but the old whole-window silence gate returned SILENCE. The new gate requires both low RMS and voiced_fraction<0.25. A seeded 50-count noise control remains SILENCE.
- A4 runtime-consumer regression and noise negative control were added. The voice-cue blob is now 4c5641adf6758762ce0fdf616a9b2a798e6de408; integrated builder blob fb59de5040081b1407ba5cbee8f9102e9921d149; recovery SHA-256 e9b32f4935652c7a3d0d322acf9358b2cf8dba256cecdf3e94f3655c36ff3034; stage SHA-256 79a5667adda7922e06dcc260e6696ed7f6c966cf2fa2b1f0c14438e663896bfa; runtime deployer and VAD workflow pins read back.
- LOCAL_LINUX scratch reproduction PASS; full local repo suite BLOCKED (no checkout/DNS). all 8 workflows on code-bearing SHA e28982337ca714fb4d14a3a972f3beafacc248c4 pass. The RAW EAR audio suites each report 75 passed on Python 3.13 and 3.14; native libfvad comparison, staged/integrated and Core same-turn also pass. The later docs-only branch head ec54bac83fe293cc9f0ff90d7fde1f029593426d has separate workflows queued. NOT_RELEASED / REDMI_UNVERIFIED.
- Private V13OBS #115 is stale (2026-11-18; LOCAL_METADATA_ONLY, B1/B2 valid offers 0). Private read-only PIPELINE_STATUS #463 is pending; no receipt yet. No UPDATE_REQUEST or device mutation.

## Next integration contract

See RESEARCH_PERCEPTION_ANDROID_AUDIO_CAPTURE_CONTRACT_20261122.md. Core owns companion/provider and Termux bridge; QA owns permission/lifecycle/revocation acceptance; Perception owns A-plane source/finality contract and Termux consumer. Keep microphone OFF until a visible OS permission prompt and explicit local approval exist. No raw PCM persistence, no background capture, no model/weight changes.
