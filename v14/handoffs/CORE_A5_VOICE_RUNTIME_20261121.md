# Core handoff — current RAW EAR to B1/B2/C3 staged Runtime

**Date:** 2026-11-21  
**Owner:** Core & Harness  
**Branch head:** 1fa1d0513c232b1e044f57b7a1e786204a31204d  
**Dependency/base:** Perception PR #2192 branch research-perception/v14-raw-ear-runtime-temporal-state-20261121 at 3df5bfd415978db3d8f958bd46522697cbd61bbe  
**Status:** staged candidate; CI pending; NOT_RELEASED; REDMI_UNVERIFIED.

## Product gap

The current release has caller-supplied RAW EAR input modules, but the existing Runtime consumer does not yet pass the consent-bound acoustic features through B1_DETAIL and B2_GIST into C3_LANGUAGE. The older Core PR #2158 was pinned to stale source revisions and is 215 commits behind the current release. This branch ports only the Core-owned stage/build/deploy composition onto the current Perception producer, without changing Perception-owned files.

## Connected implementation

- Current Perception producer pins: audio_voice_cues.py Git blob 4ddb61865deb56b0048390740d35770d4d89316e and audio_temporal_evidence.py 098ce2ec6bb0b744166d711a3401b7acf0252de1; Runtime and cognition pins are 30360f40eb784be5ea975ee85e94a57f0b154164 and 06de0acf2c6d30d50301d5073f5569822edff813.
- integrated_audio_context_candidate_20261121.py adds a bounded, consent-rechecked audio_window to the staged Runtime, runs A5/A4 acoustic feature extraction, records source-bound audio context, and exposes it separately to B1/B2 and C3. Raw PCM and consent callbacks remain process-local; audio features are not transcripts, quotable text or learning/action authority.
- The staged body QueryPacket and OfferPacket carry the same audio context refs. The C3 context carries the same acoustic feature layer while preserving text source lineage.
- The current recovery builder now pins the date-aware arithmetic reflex; date-shaped subtraction requires an explicit calculation cue. Built-in arithmetic remains LOCAL_EXACT_ARITHMETIC and is explicitly tested not to become an operator-approved fixed rule.
- The stage builder and runtime deployer pin the new wrapper and stage by exact SHA256. The source files remain frozen; the candidate is staged for review only.

## Exact SHA256 chain

- arithmetic_reflex.py: 3874df3a75137239336e42af304437531562c96eff8323b0d8cd6dd43c3cc653
- integrated_arithmetic_candidate_20261116.py: 728a229ea8316aa97fdd8cf83fa7d5358bc1c187cfcc556b62005e9e0e872128
- termux_runtime_recovery_candidate_20261112.py: ff0920afd2311827678ff9cfa115c63cd4ff06cda3a9cddf5f298fd4719ad9d5
- integrated_audio_context_candidate_20261121.py: 1a3ccb0160706c1c5fc39f67cb91ed2f8083a481519b558f16ead8109304f238
- termux_runtime_recovery_candidate_20261121.py: d495452982268e96d66ba6fdf491759f0bbbdcd828a33ace7b87e5ca728bd6d5
- stage_integrated_candidate.py: 8d68f2bbae90f28675c35bec22b04834bbd2732aad40e2ea1e2217596cc06cba
- runtime_deploy.py STAGER_SHA256 points to the stage hash above.

## Test/evidence boundary

- LOCAL_LINUX full checkout and repository pytest: BLOCKED; git ls-remote failed because github.com could not be resolved.
- LOCAL_LINUX isolated arithmetic_reflex compile and positive/date/negative tests: PASS 3/3 on Python 3.13.5 from exact branch readback; not a full repository or staged Runtime test.
- LOCAL_LINUX: source/blob and SHA256 chain readback verified from GitHub contents; no claim of a full local build or Runtime test.
- CI: pending on this exact branch. Workflow covers Python 3.11/3.13, staged Runtime composition, synthetic PCM16 with explicit consent callback, B1/B2/C3 prompt consumption, source/PCM privacy, arithmetic policy separation, stage persistence and deployer pin checks.
- The audio Runtime test uses a synthetic tone and fake body/language runners. It is a WIRED_SYNTHETIC E2E test, not real microphone, native model, or Android hardware proof.
- REDMI/TERMUX: UNVERIFIED. No live phone receipt, microphone permission grant, installed SHA or native measurement.
- No microphone, model download, weights, user data, Android permission or deployment was changed.

## Next action

Wait for exact-head CI. Fix any failed staged consumer or hash-chain regression. If green, request Boss/Integrator review because the stage builder and runtime deployer are production deployment surfaces; do not bypass the safe-additive gate. This PR depends on #2192 and must be rebased/retargeted after that dependency is merged. Only then consider the normal verified updater path and a separately consented real-device audio test. Full speech decoding/vocoder, trained voice learning, full-duplex output and persistent learned audio adaptation remain open.
