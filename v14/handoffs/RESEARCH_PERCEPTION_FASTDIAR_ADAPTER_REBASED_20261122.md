# Research & Perception handoff — FASTDIAR diagnostic adapter (rebased)

Date: 2026-11-22
Base: `gpt6/v13-private-remote-bridge-20261111` at `aed1d2b826290c95c70356b5d8b864b5ef382be4`
Branch: `research-perception/v14-fastdiar-rebased-20261122`

## Research and licensing

- Full paper reviewed: Torgashov & Köpüklü, *FASTDIAR: Frame-Level Speaker Encoder for Streaming Diarization*, arXiv:2610.02941v1, submitted 2026-10-02; preprint, not peer-reviewed evidence.
- Official repo `microsoft/fastdiar`, release `v0.1.0`, revision `e7f9bbccf98865216f48a04868d74f1d53c8734e`.
- The repository code license is MIT. The inspected release/checkpoint artifacts do not state a separate checkpoint-weight license; weight rights remain unresolved. No weights are downloaded.
- The README specifies a float16 (n_frames, 192) matrix at 80-ms frame steps. The encoder's causal history is two seconds and the diarizer has 960-ms output delay. The paper's Small parameter count (2.7M) differs from the README (2.4M); keep the discrepancy open.
- The published CPU timing is not Android/ARM evidence; its listed dependency stack (PyTorch, torchaudio, torchcodec, NumPy, SciPy, Silero VAD, pyannote) is not a Termux-ready package.

## Implementation

This branch ports the source-reviewed diagnostic adapter and its actual RAW EAR A5→A4→C3 consumer regression onto the current release-development base:
- descriptor-relative, O_NOFOLLOW checkpoint hashing under a caller-trusted local model root;
- 192-D / 80-ms frame metadata, bounded matrix and timestamps, source/generation provenance;
- actual checkpoint bytes hashed locally; the embedding producer remains caller-supplied and is not cryptographically attested;
- no inference, weight loading/download, clustering, speaker labels, persistent vectors or calibration. A4 remains DEFER and identity/learning/action authority remain false.

## Evidence

- Source/test files are byte-identical to the previously reviewed adapter/test PR code; this PR's base is current `aed1d2b`, not the stale c4eb82 base.
- The prior exact focused CI on the same source/test bytes passed Python 3.13/3.14, including the real `consume_pcm16_voice_window` A5→A4→C3 regression. This branch runs a dedicated exact-base workflow to repeat those checks.
- Full local Aii checkout remains unavailable in this worker due GitHub DNS resolution; no local full consumer suite is claimed.
- No FASTDIAR inference, checkpoint weight download, ARM/Termux, Android microphone or Redmi timing/quality test. REDMI_UNVERIFIED.

## Next

Resolve checkpoint-weight licensing and obtain a separately consented, source-disjoint labelled embedding source before any calibrated A4 decision. Keep the optional adapter diagnostic-only and A4 DEFER. Core still owns normal Runtime dispatch.


## Follow-up — exact current-PCM binding (2026-11-22)

The diagnostic embedding contract is now version 2. Each supplied frame batch must carry `current_chunk_sha256`; the RAW EAR consumer independently hashes the PCM16 bytes it actually received and rejects a mismatch before the speaker registry mutates temporal history. Accepted diagnostic evidence reports `source_binding_status=CURRENT_PCM_CHUNK_SHA256_MATCH`. The hash is provenance only; no PCM or embedding vector is persisted.

This closes an accidental/cross-source mix-up between caller-supplied frame embeddings and the current PCM chunk. It does **not** attest that FASTDIAR produced the vectors, nor does it attest the model's preceding two-second recurrent state. No identity, calibration, learning or action authority is added; A4 remains DEFER.

Added negative controls at both registry and actual `consume_pcm16_voice_window` A5→A4→C3 consumer levels. A mismatched chunk hash must yield REJECTED/DEFER and no speaker-similarity summary. The positive consumer path asserts the exact PCM digest match.

LOCAL_LINUX CPython 3.13.5 isolated hash-binding helper: 5/5 PASS (matching digest plus malformed, missing, uppercase and mismatched negative cases). Full Aii checkout remains unavailable in this worker; exact repository tests are delegated to the new PR-head CI. No FASTDIAR inference, weight download, AudioRecord, Android/Termux or Redmi test was performed.


## Exact-head integration follow-up (2026-11-22)

- Corrected code head: `39212b5c2879901fab2f58e6156e21260297edf0`.
- The first v2 adapter/registry matrix `45059040221` compiled all five modified modules but exposed one real fixture error: the silence case supplied a speaker batch hashed from the default tone while the actual PCM was all-zero silence. The consumer correctly rejected the mismatch; the test was corrected to hash the actual silence PCM before asserting the independent SILENCE→DEFER behavior. That correction is in the current head.
- Staged/integrated run `45059040222` remains **FAIL** because the Core-owned staged builder `v13/code/scripts/integrated_audio_context_candidate_20261121.py` still pins `v13/audio_voice_cues.py` to `b18e450162b062b09368a12b1ca18924ed8c5025`. The current Perception blob is `81ae3e453c9ef378b072dfc9d243098427e24baa`. The stage therefore raises `ValueError: audio source blob changed: v13/audio_voice_cues.py`; downstream migration tests report PARTIAL because staging did not complete. The Perception PR deliberately does not edit this Core-owned pin file.
- The corrected head triggered new exact-head runs: staged/integrated `45059491887`, privacy scan `45059491947`, revocation QA `45059491914`, prosody/attention `45059491906`, FASTDIAR adapter `45059491925`, optional NumPy `45059491910`, and libfvad comparison `45059491897`. Their results must be read back; QUEUED is not PASS.
- Required Core coordination: rebind the staged source pin to the exact current `audio_voice_cues.py` blob above, then recompute any downstream nested pins and rerun staged/integrated and two-checkout migration. Do not bypass the source-pin guard.

## Research update — ER-JEPA and differential retention (2026-11-22)

### ER-JEPA — replay supplements, rather than replaces, JEPA

- **Paper:** Jingnan Pu, Zi-En Fan, Feng Lian, *ER-JEPA: Experience Replay Improves Joint-Embedding Predictive Learning in Language Models*, arXiv:2609.36952v1, 2026-09-29. Full 20-page preprint read: https://arxiv.org/abs/2609.36952 and https://pdfs.assets.alphaxiv.org/2609.36952v1.pdf. No peer-reviewed publication or official code license/repository was verified in this review.
- **Method:** keeps the ordinary next-token and paired-view JEPA losses, then retrieves old source/target pairs and re-encodes both with the **current** model. The replay path applies both token and representation losses to those old pairs. Content-based, uniform and hard replay share the same path; replay is removed after training.
- **Evidence:** Llama-3.2-1B-Instruct, LoRA rank 512, learning rate 1e-5, six epochs, five seeds, four NVIDIA A800 GPUs. On NL-RX-SYNTH at matched 240.31 PFLOPs, content replay reports 83.65±1.48% exact match versus 68.75±4.92% for LLM-JEPA; uniform replay 85.04±0.54%, versus 81.24±1.12% for a current-batch replay-loss control. The paper also reports fewer previously correct predictions becoming incorrect (6.65% vs 8.85% for LLM-JEPA in the five-seed comparison). These are high-compute training results, not mobile learning measurements.
- **Limits:** the method requires paired views and grid-search tuning of replay weight β. It uses large offline training compute; no Android/ARM, small on-device adapter or online microphone result. The authors explicitly leave adaptive weighting and more general paired-view construction as future work.
- **V14 experiment implication:** preserve JEPA and add a bounded replay supplement only for explicitly consented, source-bound paired experiences. Recompute with current weights; do not replay stale embeddings as if they were current. Compare content/uniform/hard/no-replay and current-batch controls under equal update/replay-byte budgets; record gradient and parameter diffs, old/new source-disjoint retention, revision latency, restart and rollback. This does not authorize raw private conversation capture or automatic model updates.

### Differential retention for a changing world model

- **Paper:** Nishit Anand, Ramani Duraiswami, Dinesh Manocha, *What Should World Models Forget? Stratified Retention for Continual Adaptation*, arXiv:2610.03713, 2026-10-02. Full text reviewed: https://arxiv.org/abs/2610.03713. It is a position paper, not an empirical benchmark.
- **Proposal:** separate knowledge by the timescale for which it remains true: invariants (physics, object permanence, geometric/action-effect consistency), long-lived regularities, short-lived configuration and transient state. Report invariant-regression probes and revision latency separately; a single forgetting score rewards a frozen model and cannot distinguish correct revision from catastrophic forgetting.
- **Limits:** the authors state that rigorous probes currently exist mainly for physical invariants; geometric/causal probes and reliable estimation of each fact's invariance timescale remain open. There is no proof that invariants are localized in a learned representation.
- **V14 implication:** replay must not indiscriminately preserve stale room/object state. The future World/Self/Memory acceptance suite should track (a) invariant regression after every update and (b) observations-to-revision for mutable facts, with no single aggregated score. This complements ER-JEPA rather than replacing it.

## OSS candidate — Soniqo speech-core / speech-android (2026-11-22)

- **Code licenses:** `soniqo/speech-core` and `soniqo/speech-android` root LICENSE files both read as Apache-2.0. The Android repository is Kotlin SDK + JNI over the C++ engine; model wrappers and pipeline orchestration are in the submodule. The model weights have separate licenses.
- **Model/runtime facts from current upstream README and model cards:** Parakeet-EOU 120M ONNX bundle is 153 MB with 232 MB peak in the project's Galaxy S23 Ultra CPU table; the exact 160-ms export's model card says English-only and NVIDIA Open Model License, not Apache. Its 8/6 synthetic transcript cases and 632-ms median EOU (496–896 ms) do not establish WER or conversational endpoint accuracy. Silero VAD v5 is MIT and under 10 MB peak in the same S23 Ultra table. Kokoro-82M ONNX is Apache-2.0, 155 MB FP16 stored weights, but ONNX Runtime materializes FP32 weights at load; the Android README reports about 640 MB peak on the S23 Ultra. ReDimNet2-B6 source is MIT, 12.3M parameters and 192-D embeddings; it produces embeddings, not diarization or identities.
- **Architecture fit:** the C++ pipeline offers VAD/STT/TTS interfaces and barge-in, so it may be a reusable optional speech-effector / teacher-ASR path. It must not replace RAW EAR: keep raw acoustic/prosodic/non-speech features and source provenance independently. The Parakeet model card's English-only statement conflicts with the Android README's broader language table; treat the exact weight/model-card revision as authoritative until reconciled.
- **Hardware caveat:** published peaks are Galaxy S23 Ultra, not Redmi Note 10 Pro. ASR 232 MB + TTS 640 MB already exceed a 1-GB concurrent budget before V13 bodies; sequential load/unload may be worth testing but is unmeasured. No dependency, model, weight, language pack or APK was downloaded or installed.
- **Decision:** RESEARCH_ONLY / NO_DOWNLOAD / NO_SWAP. First audit Android API/ABI, submodule revision, ONNX Runtime providers and complete transitive licenses; then measure serialized RSS/TTFT/quality on the actual Redmi only with explicit download/test consent.


## Addendum 2026-11-22 — Optional timed Teacher Ear

- **Implementation checkpoint:** code + tests + research ledger are committed through `98d03875ffee5d1c513fc236bbcaa8ec6a9197ad` on this PR branch. New `v13/code/v13/audio_teacher_ear.py` is called by `consume_pcm16_voice_window`; the existing acoustic RAW EAR packet remains transcript-free.
- **Contract:** caller-supplied timed words are bound to exact PCM SHA-256, source ID, generation, window and FINAL/PROVISIONAL status. The path requires the current audio consent lease plus two distinct booleans (`teacher_opt_in` and `teacher_transcript_consent`). It caps input at 64 words / 512 summary characters, rejects network/raw-audio persistence claims, and marks model provenance `CALLER_ASSERTED_UNVERIFIED`. Only FINAL hypotheses become a separate ephemeral C3 Percept; PROVISIONAL remains out of C3. No transcript is written into the persistent RAW EAR PerceptPacket. The teacher never grants truth, speaker identity, learning or action authority.
- **Tests added:** helper validation, exact-source rejection, separate opt-ins, network/raw persistence rejection, bounded timestamps, finality, C3 delivery, transcript non-persistence and denial-before-persistence are covered in `test_audio_speaker_evidence.py`.
- **Local evidence:** isolated helper tests ran on LOCAL_LINUX / CPython 3.13.5 / pytest 9.0.2: `py_compile` PASS; 7/7 tests PASS. The full Aii checkout is not mounted in this runner, so the newly added repository integration tests have not been run locally; GitHub CI is the next check.
- **Runtime/device boundary:** this adapter is not yet connected to the ordinary Android audio ingress. The release Runtime at base `aed1d2b826290c95c70356b5d8b864b5ef382be4` and Boss candidate `bae7d03196d98ac6dfebc0a2649faf257ba8308f` do not expose the staged `audio_window` dispatch in `runtime.py`; `audio_input.submit_audio_only` therefore still has no proven live Runtime consumer. No Android `AudioRecord` provider or Redmi receipt was available: `REDMI_UNVERIFIED`.
- **Research:** R-094 records `k2-fsa/sherpa-onnx` v2.0.3 / Apache-2.0 code, Android arm64 NDK/JNI support and the separately Apache-2.0 English-only 20M Zipformer model card. Its int8 encoder artifact is 42.8 MB, but no runtime RSS/TTFT/quality measurement exists and it is not a German conversational model. No code dependency or model weights were downloaded.
- **Next owner/action:** Core should wire the optional teacher result through the existing audio-window Runtime path without merging transcript text into the persisted acoustic packet; QA should verify a visible, permissioned Android `AudioRecord` source and revocation behavior. Perception can then add a concrete sherpa-onnx adapter only after the exact model/weight license and device budget are approved and measured. No user action is needed for this code-only checkpoint.


## Addendum 2026-11-22 — Teacher Ear confidence and model comparison correction

- The timed Teacher Ear contract no longer requires a confidence value. ASR decoder scores are not assumed calibrated and are not converted into fabricated 0..1 confidence. Word/phrase text and timestamps remain source-bound; the summary is capped at 512 characters.
- R-095 records the alternative multilingual Whisper tiny path: 39M parameters, 75 MiB stored artifact and ~273 MB upstream memory estimate, Android example/NEON/quantization, but batch-oriented rather than true streaming. The model card's Apache-2.0 tag conflicts with OpenAI's original README statement that code and weights are MIT; the exact weight-license discrepancy remains unresolved, so no weights may be imported yet.
- The candidate comparison is now explicit: sherpa-onnx Zipformer 20M int8 is small and genuinely online but English-only; Whisper tiny is multilingual but slower/batch-oriented and has a license metadata conflict. Neither has Redmi measurements, and neither was downloaded.
- Local isolated helper test rerun after the confidence removal: CPython 3.13.5 / pytest 9.0.2, 8/8 PASS. Repository integration tests and CI remain pending; no Android or model inference proof.


## Runtime overlay review correction — 2026-11-22

- The base release Runtime at `aed1d2b` still has no audio-window dispatch. However, Boss PR #2370 does contain a staged candidate overlay that adds `audio_window` to the Runtime turn and generates `audio_context_store.py`; it is a candidate script, not a merged production Runtime. The earlier wording that the Boss candidate lacked the dispatch was too broad.
- That candidate currently pins the old `audio_voice_cues.py` blob `b18e450162b062b09368a12b1ca18924ed8c5025`, while this Perception branch now uses `5dbb0fd5e17eb9bcb190d7a3743bdd1ef1ecbb9d` and adds `audio_teacher_ear.py` blob `5a26193c94c864e6ad3af55def59bae040e59f35`. Core must update the source pin and include the new module in its candidate source map before compiling.
- The generated `audio_context_store.record()` deliberately persists only acoustic features and `transcript: None`, and filters selected Percepts to the original audio source ID. That correctly prevents teacher transcript persistence but also excludes the derived Teacher Ear Percept. Core needs a separate C3-only ephemeral hypothesis layer under the same live consent lease; do not reuse the original source ID or write teacher text to Store/saved context/logs.
- Core integration still needs exact tests for teacher-result forwarding, PROVISIONAL exclusion, revoke-before-C3 and revoke-after-finalization, and absence of transcript text from all durable packets/context. No Android AudioRecord provider or Redmi receipt is present.


## Latest available private device receipt — 2026-11-22 22:33 UTC

- The most recent owner-consented V13OBS snapshot available during this run still reports installed release `aed1d2b826290c95c70356b5d8b864b5ef382be4`, auto-update enabled, and dashboard/runtime `UP_TO_DATE` with no updater error. This is update transport evidence only.
- The last stored turn (no new CHAT_SEND or user turn was triggered) was 57.74 s total with about 41.63 s TTFT, 38.95 s C3 prefill and 2 generated tokens. B1_DETAIL and B2_GIST remain `TIME_BUDGET`; no valid offers were delivered. C3's short probe was 3.1 s; native probe `SMOKE_PARTIAL`.
- The instantaneous native process sample reported 0 mapped processes and unknown child-group readability; it is not a sustained-residency measurement. HEALTH reported runtime unavailable while DIAGNOSTICS reported running, so the snapshots conflict. No correctness claim is possible because the last user input is redacted and no new turn was sent.
- New read-only V13READ requests for HEALTH / PIPELINE_STATUS / DIAGNOSTICS were created as private issues #638–#640 and had no receipt at the time of this handoff. No LOG_PAGE, UPDATE_REQUEST, CHAT_SEND, shell, model/weight change or device mutation was issued.
