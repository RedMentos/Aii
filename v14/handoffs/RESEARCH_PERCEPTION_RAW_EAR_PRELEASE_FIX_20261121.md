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

## Verification boundary after exact PR CI

- **PR:** #2226, ready for review; head `2480bd80a173caf6bcfb0ddb18c5ce184281f5a5`, base `6c444e1dfdea19583002519a682fd64bca465098`. NOT_RELEASED.
- **RAW EAR producer/temporal/Silero/A4→C3:** 51 passed on Python 3.11 and 51 passed on Python 3.13.
- **Consent preflight/revocation/non-reentrant provider:** 27 passed.
- **VAD comparator:** 8/8 on Python 3.13 and 3.14; pinned native Linux libfvad `make check` 13 PASS / 1 SKIP / 0 FAIL / 0 ERROR on both matrix jobs.
- **Privacy:** PASS. **Staged Runtime:** 249 passed / 10 skipped / 47 subtests. **Integrated regression:** 424 passed / 3 skipped / 58 subtests.
- **Local synthetic lease/transaction harness:** 5/5 PASS. **Exact local Aii suite:** BLOCKED because no checkout is present and `git ls-remote` cannot resolve GitHub DNS.
- **Private device evidence:** latest found V13OBS #115 updated 2026-11-18 11:30:53Z; no newer receipt. Five metadata-only turns show B1 3/3 native failures, B2 2/2 native failures, zero valid offers and C3 prefill 41.5–63.7s. Installed SHA/updater state unknown; no live receipt in this run.
- **Redmi:** REDMI_UNVERIFIED. No authorized connected phone, microphone capture, native model test or private live receipt. No model, weight, permission or device-data change.

## Next integration

1. QA independently reviews the exact provider lease and Store rollback tests in #2226.
2. Core rebases #2200/#2211, removes callback re-entry inside audio_context_store.record()/view(), updates the producer source pin, and preserves tombstone/clear-before-C3 negative tests.
3. Run the combined producer→derived-context→C3 staged/integrated tests after that rebase.
4. Keep the P0 Redmi chat gate, microphone permission, speech decoder/vocoder and full-duplex acceptance open.

## 2026-11-21 16:41 CET — RAW EAR provenance regression and current-base alignment

- Fixed false provenance in AudioPerceptPacket.segments[0].unmeasured: pitch is unmeasured without F0; prosody is unmeasured with fewer than two voiced frames. Added silence, single-frame and multi-frame voiced assertions.
- Code commit 832f033cb97b5ed50fb5b3e4a9d0549cf986e06a; test commit cbaecd64fc77f1e1ac05f092a5080f54a87fe631; comparator pin commit 3868383b4ccac1b709d6310ed69bb53b9e924b47. Source blob 9cae3b93388ea2c488e5af37a544ed0df5727f07; test blob 6da1844a27c1a89affaa1b69d176ff9428dc7daf.
- Exact CI: RAW EAR 53/53 on Python 3.11 and 3.13; consent 29/29; comparator 8/8 on Python 3.13/3.14; native Linux libfvad 13 PASS per job; privacy PASS; staged 249/10/47; integrated 424/3/58. The earlier comparator failure was only a stale exact-source hash pin; it was corrected and rerun green.
- Current base includes #2228 C4 source-span integration in the normal staged Runtime. Its body models remain synthetic and its post-merge push workflows were still in progress at readback.
- Local full suite remains BLOCKED by GitHub DNS. No Android/Bionic or Redmi evidence. No microphone permission, model/weight, Age, updater or device data change.
- FD-VAD TurnBench is gated by at least 1 s of post-speech silence; its 0.853 EOT recall at FP 0.097 is accompanied by 1,019 ms median commit latency. The 190 ms/2% point is a separate operating point. No model imported.
- Core #2200/#2211 still need the non-reentrant lease token path, derived-context tombstone/clear and final pre-C3 consent check. QA review of #2226 remains required.

## 2026-11-21 16:51 CET — rebased-head CI completion and review gate

- PR #2226 is based on current integration f279286a4453248004c670fcaabecd85da6ab299; PR head 2c09d30dec1ab01fe77f1f49de2ab99e4cd60a65; code-bearing head 3868383b4ccac1b709d6310ed69bb53b9e924b47. The current integration branch has 19/19 associated workflows SUCCESS. Boss #2228's C4 source-span rule is in the normal staged Runtime, but its body runners remain synthetic.
- Exact PR-head checks: RAW EAR 53/53 Python 3.11/3.13; consent 29/29; comparator 8/8 Python 3.13/3.14; libfvad 13 PASS / 0 FAIL per job; privacy PASS; staged 251/10/47; integrated 424/3/58; integration check PASS. Safe-additive failed because this PR modifies existing workflows and shared V14 docs; no bypass. Boss/QA review remains required.
- Local full Aii suite remains BLOCKED by GitHub DNS. No native Android/Bionic, microphone or Redmi proof. NOT_RELEASED / REDMI_UNVERIFIED.
- Next: QA review #2226; Core #2200/#2211 must fix lease re-entry, derived AUDIO_ACOUSTIC_CONTEXT tombstone/cache cleanup, and hold the provider lease through final C3 generation.
