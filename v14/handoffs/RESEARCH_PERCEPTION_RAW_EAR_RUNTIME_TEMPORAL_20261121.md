# Research & Perception handoff — RAW EAR temporal Runtime state and comparator

Date: 2026-11-21 11:29 CET  
Queue: V14-006 / Research & Perception  
Release base: d4834ebb6e550064409fc146dbd59d47d7259bb5  
Branch: research-perception/v14-raw-ear-runtime-temporal-state-20261121  
Status: code candidate; exact focused CI pending after the concurrency regression; NOT_RELEASED; REDMI_UNVERIFIED

## Functional change

1. consume_pcm16_voice_window(..., temporal_state=None) now defaults to a per-Runtime TemporalVoiceEvidenceRegistry, keyed by source/generation, internally RLock-protected and LRU-bounded to 16 streams. It stores only scalar evidence/timestamps, removes older generations for a source, and supports explicit reset. Failed consent rechecks clear runtime-held and caller-supplied state.
2. Concurrency correction: first-use get/create/set of the Runtime registry is now protected by a short module-level initialization lock with a second read. This prevents concurrent first audio calls from constructing separate registries and splitting temporal history.
3. The offline comparator measures onset/offset from actual smoothed state transitions at the end of the state-changing 40 ms window, reports signed early/late delay, retunes libfvad when direct callers change sample rate, and rejects PCM tails that would otherwise be silently discarded by the 20 ms hop.
4. WebRTC remains a test-only baseline. No production dependency, native library, model, weight, microphone permission, Android behavior or device state is added.

## Exact test status

- Previous exact head c63b31d3e91523a6119b13aa1d564244247d0316: GitHub Actions RAW EAR comparator run 44894267443 PASS, model-lab run 44894267487 PASS, private-bridge run 44894267459 PASS. These validate the pre-concurrency code only.
- New focused RAW EAR producer/temporal/A4/C3 workflow is expected to run on the new test-file commit; result is pending and must be read from the exact new head.
- LOCAL_LINUX exact Aii checkout: BLOCKED — git ls-remote https://github.com/RedMentos/Aii.git HEAD fails because this worker cannot resolve github.com. No local exact-source compile or pytest PASS is claimed.
- TERMUX/REDMI: REDMI_UNVERIFIED. No connected handset, microphone permission receipt, Bionic libfvad build, PSS/CPU/battery measurement, installed SHA or deployment receipt.

## Consumer and Canon boundary

- The function is a real source-bound adapter consumer: caller PCM16 → AudioPerceptPacket → temporal A4 salience → bounded C3 admission candidate. Its temporal state is now continuous by default within a Runtime and safe against first-use registry races.
- This remains a caller-supplied PCM16 adapter, not normal Runtime microphone capture. It does not provide trained VAD, ASR, speech decoder/vocoder, full-duplex, audio learning or native B1/B2 model execution.
- Core PR #2158 still must rebase and pin the exact V3 producer plus audio_temporal_evidence.py, preserve the ordinary text PerceptPacket, carry audio context through QueryPacket/OfferPacket, and prove both B1/B2 offers reach C4/C3. Synthetic adapter tests do not satisfy that E2E gate.
- This does not provide trained B3 latent transfer, native GGUF weight updates, Android UI/API control or whole-Canon acceptance.

## Research / licensing

- The VAD comparison remains diagnostic. The existing ledger R-018 records dpirch/libfvad BSD-3-Clause plus separate WebRTC PATENTS text and the MIT wrapper / WebRTC-derived C provenance caveat for webrtcvad-wheels==2.0.14.post1.
- Linux aarch64 wheels are not Android/Bionic evidence. No dependency or external code was imported into the product.
- No new paper is claimed in this checkpoint.

## Next executable step

Read the exact new focused CI (Python 3.11 and 3.13) and privacy scan. If green, update this handoff/PR evidence and ask Boss/QA to review the current-base producer. Core then pins the exact source blobs and tests the full staged Runtime path. Only an authorized Redmi run can measure microphone onset/offset, CPU/RSS/battery and installation state. No user action is required for this repository-side checkpoint.
