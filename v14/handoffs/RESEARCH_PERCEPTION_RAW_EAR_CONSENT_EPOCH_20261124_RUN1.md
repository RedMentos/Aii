# Research & Perception — RAW EAR speaker consent-epoch isolation

**Date:** 2026-11-24  
**Branch:** `research-perception/v14-speaker-consent-epoch-20261124-run1`  
**Stacked base:** Boss PR #2443 branch `boss/v14-memory-forget-lifecycle-composition-20261123-run11-clean` @ `cdf6b64067ac426ba32194100d3764f6e74c105f`  
**Release-development base beneath the stack:** `gpt6/v13-private-remote-bridge-20261111 @ 8d93236c753f0194224c19edc7411d8d7082b1d6`  
**Release status:** NOT_RELEASED. The stack must wait for Boss PR #2443 review/integration and then Core's source-pin rebind.

## Defect and hypothesis

The speaker-similarity registry was keyed only by `(source_id, generation_id)`. Its normal revocation reset clears that state, but the registry itself did not compare the current provider consent receipt. If a source/generation identifier were reused after a new consent session and an upstream reset were missed or delayed, old speaker-reference embeddings could influence the new session.

The receiver now enforces the active consent epoch directly. This is defense in depth; the provider lease remains the authoritative permission boundary.

## Implemented code

- `v13/code/v13/audio_speaker_evidence.py`: schema v3; requires the opaque receipt in both batch and current-consumer arguments; keys RAM-only state by source/generation/receipt; deletes old receipt state and returns WARMUP on epoch change; rejects a batch with a mismatched receipt; optional receipt-targeted reset.
- `v13/code/v13/audio_voice_cues.py`: passes the exact current `AudioConsentLease` receipt into the speaker registry. The receipt is not copied into the persisted PerceptPacket evidence.
- `v13/code/v13/audio_fastdiar_adapter.py`: emits the same opaque receipt in its caller-owned diagnostic batch and validates its bounded non-empty form.
- `v13/code/tests/test_audio_speaker_evidence.py`: all registry fixtures carry receipt refs; adds direct epoch-isolation and full RAW EAR A5→A4→C3 consumer regression.
- `v13/code/tests/test_audio_fastdiar_adapter.py`: exact schema and receipt assertions; adapter calls updated.
- `v13/code/experiments/benchmark_raw_ear_backends.py`: benchmark fixture uses an explicit synthetic consent epoch.

## Exact readback blobs

| File | Git blob SHA |
|---|---|
| `audio_speaker_evidence.py` | `33603864c5b730a302da76572ec5708e837685fd` |
| `audio_voice_cues.py` | `075726f5ee3a4bb6da9d073221afa1c90ff4ce1d` |
| `audio_fastdiar_adapter.py` | `995d74e3d40103b8787493a54b5397fc909fc1b6` |
| `test_audio_speaker_evidence.py` | `cecedd391298b78e5781a37cb23d23aee700324e` |
| `test_audio_fastdiar_adapter.py` | `6cea6bfd1b4dec2681cdec8961377fb6d53ed198` |
| `benchmark_raw_ear_backends.py` | `afcc8d48f4b5af4580e801ae00f69ebc8a9b1a14` |

Research ledger entry R-115 appended to `v14/V14_RESEARCH_LEDGER.md`.

## Test evidence and limits

- LOCAL_LINUX isolated algorithm reproduction: `py_compile` PASS; `pytest` 4/4 PASS. It verifies same-epoch continuity, new-epoch purge/WARMUP, stale batch rejection and targeted/global reset. It is **not** the exact repository module.
- Full Aii local suite: BLOCKED / NOT_RUN. No repository checkout is mounted; `git ls-remote` to GitHub fails with DNS resolution error.
- Exact repository CI: pending after PR creation. Required workflows are `V14 FASTDIAR diagnostic adapter` (Python 3.13/3.14 compile + registry and real A5/A4/C3 tests + privacy scan) and dependent staged/integrated checks.
- CI is not Redmi evidence. No phone is connected; no microphone, Android provider, Termux, native model or permission path was exercised. REDMI_UNVERIFIED.
- No model or weights downloaded, no installed model/data/permission changed, no UPDATE_REQUEST or device command sent.

## Integration coordination

This is explicitly stacked on Boss PR #2443 because that candidate contains the source-bound FASTDIAR/Teacher-Ear/A4 consumer code. It does not edit Boss-owned runtime composers or source pins. Once reviewed, Core must rebind the changed `audio_speaker_evidence.py` and `audio_voice_cues.py` hashes in the integrated audio composer and downstream staged/recovery pins, bottom-up. QA should then rerun the same-receipt, changed-receipt, revoke, restart, staged Runtime, integrated regression and privacy suites.

## Next executable step

Run exact PR CI. If green, request Core's source-pin rebind on the composed branch and rerun staged/integrated tests. Keep speaker decisions DEFER/uncalibrated until a licensed model and source/session-disjoint calibration evidence exist. No user action is required.
