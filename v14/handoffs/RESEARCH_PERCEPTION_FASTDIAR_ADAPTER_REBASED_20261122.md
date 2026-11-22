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
