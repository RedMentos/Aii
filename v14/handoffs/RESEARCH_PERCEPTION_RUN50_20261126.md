# Research & Perception Run 50 — A4 audio temporal path and V14 integration checkpoint

**Started:** 2026-11-26T21:23:14+01:00 (Europe/Berlin). **Checkpoint:** 2026-11-26T20:35:45.865Z (UTC).
**Repository:** RedMentos/Aii.
**Branch:** research-perception/v14-audio-temporal-window-order-20261126-run41b.
**PR:** [#2527](https://github.com/RedMentos/Aii/pull/2527), DRAFT / NOT_RELEASED.
**Parent before this checkpoint:** #2524 branch head a47907c4a0603e602581c6462ecb845211eb0445.
**Previous PR head:** a12d765e63e8c16f0ce9d388df840e1aa587a9f3.
**Functional merge checkpoint SHA:** 3834ac1cfb4947bb62d5f33aa0cc0fc7a60ca63a (two-parent merge checkpoint; first parent #2524 a47907c, second parent previous PR head a12d765).

## Why this checkpoint exists

PR #2527 was still based on an old #2524 parent (b298719), while the current parent had advanced to a47907c. Its branch was 96 commits ahead / 120 behind and not mergeable. The Perception audio files had no overlapping edits in the newer #2524 delta; the latter changed the native latent receiver, task-score, Core integration and shared status files. This checkpoint advances the existing audio work without force-push, retaining the old branch head as a second parent and using the latest #2524 tree as first parent. It does not change the V14 master or historical V13 Canon.

## Executable A4/A5 work retained

- TemporalVoiceEvidence is a deterministic RAW EAR attack/release smoother, not a trained VAD or calibrated speech probability. It now rejects backward window starts before state mutation, allows equal-start cumulative windows when end advances, counts only newly observed overlap suffixes, decays through short gaps, resets across source/generation or long gaps, and exposes a reversible provisional preview state.
- consume_pcm16_voice_window accepts caller-supplied PCM16 under an AudioConsentLease/consent guard, emits A5_AUDIO PerceptPacket data, routes extracted voice/prosody/non-speech cues through A4 attention modulation, and persists an A4AttentionReceipt with source_ref, event/generation/time, FINAL/PROVISIONAL status, score vector, learning_authority=false, action_authority=false and truth_authority=0. Provisional VAD and speaker-lookback state are not committed.
- The A4 receipt is stored through Runtime.store.add_packet. However, checked runtime.py has no normal-turn call site for consume_pcm16_voice_window. This is a helper-level caller-supplied PCM path tested with a Runtime-like fixture, not an integrated normal-turn audio route.
- The A4/A5 feature-set probe consumes FINAL source-bound PerceptPackets and separately sourced later action outcomes, with session/goal stratification, within-stratum permutations and provenance checks. It remains diagnostic/synthetic; it does not update attention policy or JEPA weights.
- The predictive-closure probe is a separate research diagnostic, not a runtime organ.

## Files carried forward

Perception-owned audio source/contracts, temporal and voice-cue tests, A4/A5 feature-set and predictive-closure experiments/tests, the two dedicated GitHub workflows, the audio context candidate's Perception source pins, and the Run41–Run45 handoffs are preserved. Current #2524 workboard/workplan/next-action/ledger/coverage versions are retained; this checkpoint appends only the Run50 evidence and R-170 research entry. No Core recovery/stage/deployer implementation is changed.

## Local tests

Environment: LOCAL_LINUX, CPython 3.13.
- Scratch reconstitution of the fetched TemporalVoiceEvidence source and focused tests: py_compile **PASS**.
- pytest focused temporal suite: **17/17 PASS**.
- This scratch reconstitution is not byte-identical to the repository files; the full Aii checkout is not mounted. Full repository suite, exact source checkout, native C++ build and native model execution: **NOT_RUN**.
- GitHub DNS from the local container fails; repository files were read through the connected GitHub integration, not a local clone.

## Exact CI evidence already available (not inherited as proof for the new merge head)

- On the previous code/test checkpoint of #2527, the feature-set workflow reported **15/15 PASS on Python 3.13 and 3.14**, including the repository A4 extractor → A5 PerceptPacket integration test.
- The model-lab workflow reported **58 tests PASS**; four optional native/WebRTC tests were skipped because the pinned libfvad shared library / test-only WebRTC wrapper was not built or installed.
- Offline bridge security workflow PASS.
- These are GitHub-hosted Linux CI results, not local full-checkout tests, Android, native GGUF, learned weights or Redmi evidence. Fresh exact-head CI for the new parent-advanced checkpoint is required.
- The shared staged/integrated path has previously failed on Core-owned recovery/stage/RuntimeDeploy source pins. Those files are not modified here; Core must refresh the pin chain against the current audio blobs and the latest native receiver.

## Research R-170

Full text reviewed: Yashengjiang et al., *End-to-End Markov State Sequence Learning for Auditory Attention Decoding*, arXiv:2607.18614, 2026-07-21 preprint. A two-state CRF trains window-level EEG/speech emissions under a transition prior; on AVGC it reports 86.5% causal / 92.4% non-causal accuracy at 1-second windows, with 23.3-second mean causal switch delay. AVGC uses 13 normal-hearing participants, 64-channel EEG, two competing streams, six 10-minute trials each and participant-dependent leave-one-trial-out evaluation; one programmed within-trial switch is used. KUL/USTC are static trials; results vary by backbone. Experiments used an RTX 4090. The cited AAD-CRF GitHub URL returned 404 in this run, so code/license are unverified and no reuse occurred.

V14 implication is limited: future attention evaluation should measure sequence coherence, false flips and switch delay, not only window accuracy. The paper does not validate RAW EAR acoustic cues as EEG attention evidence. No AAD posterior or trained attention model is added; a future experiment requires a real source-bound A4 score sequence and separately sourced attended-state outcomes.

## Device, release and risks

- Latest available private V13OBS #115 remains historical (2026-11-24 09:28 UTC). New read-only relay requests #989 HEALTH and #990 PIPELINE_STATUS were created; at first check they were open with no device comments. If no later signed response appears, record NO_LIVE_RECEIPT.
- Auto-update was historically reported enabled, but the latest install/updater state is not authenticated for this run. REDMI_UNVERIFIED.
- No UPDATE_REQUEST, CHAT_SEND, remote shell, restart, model/weight/permission/data mutation or device deployment was performed.
- B3 remains OFF. Native cross-model latent exchange, native GGUF task utility, persistent weight learning, Android microphone/AudioRecord, normal-turn audio lease through C3, full-duplex voice and Redmi behavior remain unverified.
- Push/PR is not deployment. NOT_RELEASED.

## Next executable action

1. Core/Integrator refreshes the recovery → stage → RuntimeDeploy audio source pins and the #2525/#2523 native receiver integration against the current #2524 parent; rerun exact staged/integrated and migration gates.
2. Core adds a normal-turn caller that holds the revocable AudioConsentLease through A4 admission and the complete C3 generator; keep the fast text path and deeper multi-organ path intact.
3. Perception then adds a real source/session-bound A4 score-sequence evaluation with trusted attended-state outcomes, held-out sessions, switch-delay, false-flip, drift and shuffled-outcome controls. Do not map EEG AAD results directly onto acoustic cues.
4. No model swap or user action is needed. Keep microphone capture OFF until the Android provider, consent/revocation and zeroization path are independently verified.


## Parent #2524 CI failure readback after this checkpoint

Exact workflow 45890208766: Linux pinned API PASS; Android arm64 cross-compile PASS; Python 3.13 and 3.14 each report 92 passed / 1 failed. The sole failure is test_native_receiver_is_composed_and_runtime_contracts_pass, which reaches integrated_observer_fair_budget_candidate_20261116.py and raises ValueError: observer fairness source changed: v13/cognition.py. Exact shared staged/integrated workflow 45890208703: 20 failed, 233 passed, 10 skipped, 2 errors, 41 subtests passed. The same stale observer fairness pin causes the staged failures; two migration tests additionally expect UPDATED but receive PARTIAL. This is a Core-owned source-pin/migration chain, not a Perception audio test failure. Perception did not alter Core recovery/stage/deployer files. Core/Integrator must rebind and retest.


## Core replacement PR #2538

After the parent #2524 failures recorded above, Core opened replacement PR #2538 (branch core/v14-native-receiver-kv-integration-20261126-run50-core, head ddeca6a939399786753ecc6ae13086a99e68802e) and reports refreshing the observer/recovery/audio/stage/RuntimeDeploy pin chain against the current #2524 parent without weakening guards. Its exact-head CI runs 45891049901, 45891050110, 45891050131, 45891049890, 45891049926 and 45891049936 were QUEUED at first poll (only the Lab Age control check 45891052157 had completed PASS). This is not yet a verified fix. #2538 is based on #2524, not #2527; after #2527 exact A4/A5 CI is green, Core must stack/rebase #2538 onto the #2527 audio branch and refresh the A4 audio pins. Perception will not edit Core-owned recovery/stage/deployer files.


## Exact audio pin mismatch in Core #2538

Current #2538 branch source: integrated_audio_context_candidate_20261121.py blob 831080bceec90711bd42e0fa4eba47c669975c98. Its current expected pins are audio_voice_cues b18e450162b062b09368a12b1ca18924ed8c5025, audio_temporal_evidence 098ce2ec6bb0b744166d711a3401b7acf0252de1, and contracts 7b21d9c5076015716851b5d432a5730e4e17da92. Current #2527 blobs are audio_voice_cues b372d52b83c1b35077732755f076e48b62e90ac0, audio_temporal_evidence cacf649007a89cbfe74924536e413747d1392db3, and contracts 6065a471f5f623abea57725d33d362d9eb806013. Thus #2538 is refreshed for #2524 but not yet for #2527. A Core-owned stack/rebase and exact pin refresh is still required after #2527 CI; do not modify Core files from this lane.


## Run50 code/test and exact CI readback

**Additional code/test commit:** 13999de8c676f07075cb8a0d3f0165b579d6cdc6. It fixes a reproduced Perception-owned source pin in integrated_audio_context_candidate_20261121.py: v13/cognition.py expected 06de0acf2c6d30d50301d5073f5569822edff813, while the current #2524/#2527 parent file is Git blob deb8c274022e2a4419dd38adb11ca14481c4bd91. The other 11 candidate source pins were checked against current GitHub file blobs and matched. Added test_integrated_audio_candidate_source_blob_pins_match_current_tree, which checks all 12 pins against the actual checkout at CI time. New candidate script blob: 5d21b77c68d6c890040b9d720fa150b7690815b7; new test file blob: 82e1473cabbcc3dc4c6a8ae7b16cb3568af438b4.

**Exact CI on code/test SHA 13999de8c676f07075cb8a0d3f0165b579d6cdc6:**
- V14 RAW EAR vs WebRTC/libfvad 45893106174: PASS on Python 3.13 and 3.14.
- V14 RAW EAR optional NumPy backend 45893106136: PASS on Python 3.13 and 3.14; each ran 117 tests in 10.41s / 16.36s.
- V14 source-bound A4/A5 feature-set probe 45893106110: PASS on Python 3.13 and 3.14.
- V13 runtime deployment integrity 45893106074: PASS.
- V13 staged context/integrated regression 45893106088: FAIL, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Root causes are Core-owned pins: old recovery AUDIO_BUILDER_BLOB_SHA1 831080… instead of candidate blob 5d21b77…; arithmetic SHA-256 pin for contracts.py (current Git blob 6065a47…); observer fairness pin for cognition.py; two migration PARTIAL-vs-UPDATED assertions. Do not treat the passing independent workflows as staged-system acceptance.

**Core coordination:** PR #2538 head ddeca6a939399786753ecc6ae13086a99e68802e now passes its own #2524-based native receiver Runtime consumer, RuntimeDeploy, controller guard, migration, owner-read bootstrap and staged/integrated workflows (45891049936, 45891049901, 45891050110, 45891049890, 45891050131, 45891049926). It is still based on #2524, not #2527. Its recovery audio builder and arithmetic pins still target the old Perception audio blobs. Core must stack/rebase #2538 onto #2527, update the builder and contracts pins, preserve observer/migration fixes and rerun combined staged/integrated.
