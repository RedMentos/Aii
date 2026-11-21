# Research & Perception — RAW EAR consent lease on current integration head

**Date:** 2026-11-21 16:00 CET  
**Base:** `6c444e1dfdea19583002519a682fd64bca465098` on `qa/v14-jepa-checkpoint-publication-20261121`  
**Branch:** `research-perception/v14-raw-ear-consent-current-20261121-run11`  
**Canon:** A0–A5 / A4 active attention / source-bound A5 / STEP9–G10C–G10D VOICE_AUDIO / #1984; P0 interaction remains #1904.

## Defect and correction

The earlier producer candidate acquired the provider lease before PCM processing, but then called `consent_check` again inside that lease (and again before C3 admission). A provider backed by an ordinary non-reentrant `threading.Lock` can deadlock or reject its own already-authorized consumer. The callback also created a second, weaker authorization path that contradicted the lease contract.

The current-head port changes the boundary:

- the metadata-only preflight check happens before the lease;
- the provider lease is then acquired and must yield the literal `True`;
- no provider callback is reacquired while the lease is held;
- the same lease remains held through PCM observation, feature extraction, optional VAD state, packet transaction, temporal evidence, A4 attention and C3 admission;
- Store failure still rolls back the packet transaction before attention;
- a revocation that wins between preflight and lease entry rejects before any PCM-derived work; a revocation that starts after lease entry waits until the bounded consumer exits.

The QA-owned deterministic preflight/revocation and non-reentrant-lock tests are carried into this current-base branch. The old callback-count test is replaced by a Store commit-failure rollback regression because an uncoordinated boolean callback is not a valid substitute for the required linearizable lease.

## Executable path

`caller PCM16 → audio_voice_cues.consume_pcm16_voice_window → audio_ear.observe_pcm16 → voice/prosody cues → optional Silero VAD stream → source-bound AudioPerceptPacket → Store transaction → temporal voice evidence → A4 attention → C3 admission`.

This is still a caller-supplied PCM adapter, not microphone capture. It does not persist raw PCM, identify speakers, perform ASR, grant learning/action authority or run native model inference. Optional Silero requires a caller-supplied, revision/hash-checked local ONNX session; no model download or runtime dependency is added.

## Research notes

- FD-VAD (Mathur & Manocha, arXiv:2609.35791v1, 2026-09-16) motivates a future separate semantic `TURN_STATE` decision, not replacing acoustic A0–A5. The TurnBench headline is 0.853 EOT recall at FP 0.097 with 1,019 ms median commit latency; the paper's separate 190 ms / 2.0% false-interruption point is a different operating point. Its reported 45.8 ms/window is on one NVIDIA A100. The official model card is MIT but English-only and lists a 119 MB adapter and ~1.5 GB self-contained bundle; no Termux/Redmi adoption is justified.
- S4VAD (Cohen et al., arXiv:2609.11110v1, 2026-09-10) motivates event-level onset-latency measurement with annotation uncertainty. No official implementation/license was verified; no import.
- The pinned libfvad comparator remains a test-only Linux comparison. Its results are not Bionic/ARM/Redmi measurements.

## Verification boundary at commit creation

- Exact local repository suite: BLOCKED; no full checkout is available and `git ls-remote` cannot resolve GitHub DNS in this runner.
- The local Python environment is available for a small isolated lock/transaction semantics check; that is synthetic, not the exact repository test suite.
- Exact PR CI must run the producer regressions, staged/integrated guards and privacy scan before this candidate is ready for independent review.
- Redmi: REDMI_UNVERIFIED. No connected authorized phone, microphone capture or private receipt was obtained.
- Release/deployment: NOT_RELEASED. No update request, model/weight change, permission change or device data mutation.

## Next integration

1. Run exact current-head Python 3.13/3.14 RAW EAR tests and the preflight-revocation/non-reentrant-lock regressions.
2. Have QA independently review the provider lease contract and the failure/rollback tests.
3. Core must port the same lease through derived audio-context persistence and recheck/tombstone before C3 native generation; this producer PR alone does not close #2211/#2200.
4. Keep the P0 20-turn Redmi chat gate, microphone permission, speech decoder/vocoder and full-duplex acceptance open.
