# Research & Perception — Run 36 — 2026-11-24

## Checkpoint

- Repository: `RedMentos/Aii`
- Working PR: [#2448](https://github.com/RedMentos/Aii/pull/2448)
- Branch: `research-perception/v14-audio-duplex-bridge-20261123-run21`
- Base: `8d93236c753f0194224c19edc7411d8d7082b1d6`
- Latest code/test checkpoint: `1c472abd672ab8e2838db48f80b5a252b6336aae` (initial candidate checkpoint `677f73eaf7bf594ecbbf64ab2e99cca4398e0bc1`)
- State: OPEN / DRAFT / NOT_RELEASED.

## Functional change

Implemented an additive RAW EAR turn-candidate decomposition in the existing A5→A4→C3 path:

1. `speech_candidate`: sustained temporally filtered voiced activity.
2. `interrupt_candidate`: new voiced onset only; duplex still requires the user's configured interrupt mode and an active same-generation turn.
3. `eot_candidate`: one-shot candidate after 400 ms of newly observed contiguous silence following sustained voiced activity.
4. `floor_transfer_verified=False` / `UNVERIFIED`: no model is allowed to treat acoustic silence or onset as proof that conversational control transferred.

The silence clock counts only new window coverage, is reset by noise/impulses/uncertain windows, and cannot cross source, generation, consent-receipt or long-gap boundaries. The existing temporal receipt binds the new fields; the compact C3 summary exposes the candidate triad. No new model or dataset was downloaded.

## Files changed

- `v13/code/v13/audio_temporal_evidence.py`
- `v13/code/v13/audio_voice_cues.py`
- `v13/code/v13/audio_duplex_bridge.py`
- `v13/code/tests/test_audio_temporal_evidence.py`
- `v13/code/tests/test_audio_ear_voice_cues_v14.py`
- `v13/code/tests/test_audio_duplex_bridge.py`
- `.github/workflows/v14-raw-ear-prosody-attention.yml`
- `.github/workflows/v14-raw-ear-vad-comparison.yml`

The existing RAW EAR workflow now targets Python 3.13/3.14, NumPy 2.3.5, read-only repository permissions and prints exact source SHA-256 pins for the integration owner.

## Tests and evidence

- LOCAL_LINUX: isolated state-machine reproduction PASS (sustained onset, 400 ms EOT, short-burst negative, noise/impulse negative). It is not a full Aii checkout or repository test.
- CI: initial head `677f73eaf7bf594ecbbf64ab2e99cca4398e0bc1` exposed one test-fixture `KeyError` (`event` has no `session_id`) and stale VAD-comparison Git-blob pins. The fixture now retains `session` and the comparator workflow pins the new exact blobs. Expanded head `1c472abd672ab8e2838db48f80b5a252b6336aae` was pushed; RAW EAR prosody/A4/C3, audio duplex, consent, comparison, privacy and staged/integrated jobs were queued at checkpoint. Record exact conclusions only after completion.
- LOCAL_LINUX full repository tests: BLOCKED; GitHub DNS is unavailable in the local container, so no full checkout can be materialized.
- TERMUX/REDMI: REDMI_UNVERIFIED. No handset, AudioRecord, microphone, native model, RAM, TTFT or Android latency measurement was performed.
- Deployment: NOT_RELEASED. A GitHub push is not a phone deployment. No update request was sent and no device/model/permission was changed.

## Research

This is a code follow-up to R-128, not a new paper review. R-128 already records full-paper reads of Patamia et al. (arXiv:2611.19484) and Mathur & Manocha / MultiPartyTurnBench (arXiv:2610.20172). Their distinction between candidate discovery, EOT and INT verification motivates the interface. The 400 ms threshold is an uncalibrated BOOT default, not a reported paper result. MPTB's MIT code and CC BY 4.0 gated dataset were not downloaded or reused.

## Integration owner and blocker

- Boss/Integrator PR #2443 owns `integrated_audio_context_candidate_20261121.py` and `source_lifecycle_lock_integration_candidate.py`.
- This PR does not change those files and does not bypass their strict pins.
- After CI completes, send the exact updated audio source pins to #2443; Boss must compose the current #2448 audio source with current #2463 vision source, recompute strict Git-blob/SHA-256 pins bottom-up, and rerun staged/integrated/same-turn/migration tests.
- Existing audio duplex race fixes remain in place: one-shot receipt claim, first-writer target-turn ownership, durable handoff before cancellation, and rollback if the target turn changed.

## Next executable action

1. Read exact CI results for code head `677f73eaf7bf594ecbbf64ab2e99cca4398e0bc1`.
2. If focused tests pass, publish exact audio source pins to Boss/Integrator PR #2443 and link the evidence to whole-Canon issue #1984.
3. Do not claim integration/release until the source-lifecycle composer accepts both audio and vision, combined staged/integrated/same-turn/migration CI passes, and a separate consented Redmi receipt verifies installation and native microphone behavior.
4. Next Perception experiment: session-disjoint EOT/INT hard negatives and source-bound A4 outcome/retention; keep the EOT candidate SHADOW until false-interruption and latency metrics are measured.

**User action:** none required. No manual Termux command, model download/swap, device update or permission change.
