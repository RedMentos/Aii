# Research & Perception — run 37 — 2026-11-24

## Current work and user effect

Implemented a source-/generation-/consent-scoped non-speech onset gate on the existing RAW EAR → A4 path. A continuous UNVOICED_NOISE bed or overlapping IMPULSIVE windows now emit one A4 novelty onset per episode instead of repeatedly dominating attention. SILENCE/VOICED end an episode; UNCERTAIN and short gaps decay it; source/consent changes reset it.

The A4 consumer keeps absolute RMS/ZCR as low-gain background cues and explicitly keeps non-speech novelty out of external_interrupt. Therefore this can recruit perception but cannot authorize barge-in, cancel a response, change learning authority or grant Android action authority. The consumer test checks all of those negative boundaries.

E2E user effect: the synthetic audio path distinguishes a new non-speech event from a sustained noise bed. It does not change C3 answer quality, supply an Android microphone, or prove a working voice conversation.

## GitHub and exact code lineage

- Repository: RedMentos/Aii
- PR: #2448, OPEN / DRAFT / NOT_RELEASED.
- Branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- Base: 8d93236c753f0194224c19edc7411d8d7082b1d6
- Code/test commit: 6d650a7d0a1fbf4d6ab43e32a272f31919a976ec
- Comparator-pin correction: a5294d08aa4ffbe9da5fbc4c697019fa31ad56ab
- Exact readback confirmed the modified Python modules, tests and comparator workflow on the branch. No release SHA and no deployment are claimed.

Changed runtime paths:
- v13/code/v13/audio_temporal_evidence.py
- v13/code/v13/audio_voice_cues.py

Regression paths:
- v13/code/tests/test_audio_temporal_evidence.py
- v13/code/tests/test_audio_ear_voice_cues_v14.py
- .github/workflows/v14-raw-ear-vad-comparison.yml

## Tests and environment

LOCAL_LINUX
- Isolated temporal-state harness: 4/4 PASS.
- Full Aii checkout pytest/compile: BLOCKED / NOT_RUN. The container has Python but no mounted Aii checkout; git ls-remote failed due unavailable GitHub DNS. Do not relabel this as a full local test.

CI / exact branch
- raw-ear-prosody: 81 passed on Python 3.13 and 81 passed on Python 3.14.
- raw-ear-fastpath: PASS on Python 3.13 and 3.14.
- VAD comparator: PASS on Python 3.13 and 3.14 after the workflow pin was updated to the final audio_voice_cues.py Git blob.
- Offline 3.11/3.14, privacy, consent-revocation, same-repository integration and offline-bridge-security: PASS.
- At last poll, Boss-owned composition remained blocking: staged-runtime failed with 16 failed / 237 passed / 10 skipped / 2 errors / 47 subtests, all cascading from ValueError: audio source blob changed: v13/audio_voice_cues.py; consumer 3.13 had 2 failed / 3 passed for the same pin. Integrated-regression and some remaining jobs were still in progress. This is NOT a green integrated matrix.

## Integration handoff — Boss owns the composer

Boss PR #2443's current integrated_audio_context_candidate_20261121.py still expects older Perception blobs. Current #2448 source pins to rebind bottom-up:

- v13/audio_voice_cues.py: 334b396fcb72d4c4d1006e22996c344e75a0d453
- v13/audio_temporal_evidence.py: 36e30c6a0c3278ea88e7442f66be07d99f6043a7
- v13/audio_speaker_evidence.py: 14a6d8d79d361e6c89c3770d372a3f9824f13afb
- v13/attention.py: 0f6a81e7380aa6716bbac4e4ef5834d108601a70

The current audio_duplex_bridge.py blob is 41cc51bd8d08579356b99ad1d7bf1f7fc0f17121; it is not yet included in the Boss audio composer. It needs an explicit pin and composition path if the full-duplex wrapper is intended to be in the staged product. Do not copy Perception code into the composer without revalidating source/consent/receipt contracts; do not weaken byte matching.

Separate current integration blockers remain:
- Perception PR #2463's A5/vision source-lifecycle composition is still rejected as unsupported lifecycle source: vision.py by the Boss-owned composer.
- Core PR #2462's same-turn B1/B2 → C4 → C3 consumer remains blocked by downstream Runtime source pins.
- Core native receiver #2457 remains blocked upstream and production B3 stays OFF.
- Perception audio-capture consumer #2312 is still stacked on the closed QA companion branch; no AudioRecord provider or microphone capture is available.

## Research

- R-131 records the implementation and test evidence.
- R-132 records two relevant but non-adopted directions: Next-Turn (arXiv:2606.18094, abstract-only; timestamp-derived time-to-next-onset supervision) and PCL-AED (DOI 10.1186/s13636-026-00447-4, publisher abstract only; temporal contrastive acoustic-event boundaries).
- Neither paper supplied code/weights for this patch. No external model, dataset, dependency or license was imported.

## Redmi / updater boundary

Latest private V13OBS #115 readback (updated 2026-11-24 09:28 UTC):
- Installed release: 8d93236c753f0194224c19edc7411d8d7082b1d6; updater enabled and Runtime/Dashboard report UP_TO_DATE at that installed SHA.
- AI runtime is STOPPED_BY_USER; autostart is false; model process is stopped; native-residency accounting is unavailable.
- Last stored turn (not a new test): 6.295 s total, 2.046 s TTFT, 358 admitted C3 prompt tokens, 7 generated tokens.
- B1_DETAIL/B2_GIST: 0 valid offers; their latest native failures remain TIME_BUDGET at 53.2 s / 54.2 s. Native latent exchange is not proven.

No CHAT_SEND, UPDATE_REQUEST, restart, shell, microphone capture, LOG_PAGE, model/weight change, permission change or data mutation was performed. The user-stopped runtime was respected. This PR is not merged, so the new code is not deployed. REDMI_UNVERIFIED.

## Next executable steps

1. Boss/Integrator: rebind the four current Perception audio source pins in the strict audio composer; decide explicitly whether to add audio_duplex_bridge.py; then rerun staged-runtime, integrated-regression, both consumers, migration and privacy.
2. QA/Core: reconcile #2312 with a current companion AudioRecord provider and prove consent/revocation/zeroization before any device microphone path is enabled.
3. Perception: after the staged consumer is integrated, compare onset-gated A4 against the previous absolute RMS/ZCR baseline on source/session-disjoint consented audio; measure false attention events and interruption separately.
4. Later research experiment: a small time-to-next-speech-onset head can be trained from aligned timestamps, but only after source-bound dataset consent, holdout design, latency and retention gates exist.

User action required: none. No model, permission or device action is needed for this code-only checkpoint.
