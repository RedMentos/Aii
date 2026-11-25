# Research & Perception Run 20 — native tokenwise pair assembly

- Started: 2026-11-25 19:29:31 CET
- Completed: UNKNOWN at checkpoint
- Repository: RedMentos/Aii
- Release HEAD inspected: 8d93236c753f0194224c19edc7411d8d7082b1d6
- Work base: Research/Perception PR #2506 head 3b8e66ca99323b138257fc28069a8e4cb9540c13
- Branch: research-perception/v14-native-tokenwise-pairing-20261125-run20
- Draft PR: #2507
- Code/test SHA: 29cda16ef3e3ce436e5f0d59eb418c030626f024

## Delivered

Added native_tokenwise_pairing.py and its tests/docs. It composes the stored sender LatentTapPacket plus exact Cognition.read_tap data with the native selected receiver input-embedding extractor output. It checks source/event/generation/role/tap/model/tokenizer/blob bindings and aligns different tokenizers by exact UTF-8 byte-piece overlap. It returns an in-memory PAIRED_DIAGNOSTIC record only; it does not persist, fit, infer, edit weights or enable B3. LATENT_PREFIX_V1 remains separate and event-pooled.

## Tests

- LOCAL_LINUX CPython 3.13.5 isolated harness with stubbed dependencies: 7/7 PASS; py_compile PASS.
- GitHub Actions PR run 45678205802: 80/80 PASS on Python 3.13 and 80/80 PASS on Python 3.14; privacy scan CLEAN.
- GitHub Actions push run 45678196840: 80/80 PASS on Python 3.13 and 80/80 PASS on Python 3.14; privacy scan CLEAN.
- Staged/integrated regression 45678205707 was still in progress at checkpoint.
- Full local Aii checkout NOT_RUN; no real GGUF row read or Redmi proof.

## Research notes

The selected-row API is present in llama.cpp commit 2851b3bcbf8d993a2243ae751c0a7dfa8e944a40 (2026-10-15, MIT), but src/llama-ext.h labels it staging/WIP. The extractor loads a CPU model using mmap/lazy mode; 2 MiB is only the maximum selected-row output buffer, not peak RSS. The extractor and receiver use different llama.cpp pins; exact-GGUF compatibility and memory must be measured. Model-weight license remains unverified. R-150 remains abstract-only; do not generalize its near-transfer results.

## Remaining

Core must wire the two native tokenizer piece streams and selected-row extractor into the actual Cognition.tap/receiver workflow, call this helper, and persist/train only behind explicit local consent. Then run source/session-disjoint receiver utility, no-message/zero/shuffle/repeat/OOD controls, retention and restart/rollback. Redmi remains REDMI_UNVERIFIED; installed runtime remains STOPPED_BY_USER in the latest historical snapshot. No user action required.


## R-152 — mobile native-load optimization candidate

Pinned-source review found the selected-row extractor and native receiver each load the same GGUF in separate native executables. The receiver uses llama.cpp b29c606; the extractor uses 2851b3b for the staging/WIP selected-row API. Core could evaluate one executable and one loaded model pointer for both extraction and decode, after unifying the pin. This may avoid duplicate load/startup work, but mmap means RSS/PSS improvement is unknown. Benchmark exact GGUF PSS/RSS/TTFT and receiver utility; preserve all current controls. This is research only, not implemented or device-tested.
