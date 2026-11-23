# Research & Perception — run 5 handoff (2026-11-23)

## Checkpoint
- Development base inspected: b20e9b1f3dd53af472055adb43da628785494ec4 on gpt6/v13-private-remote-bridge-20261111.
- Perception PR #2433: https://github.com/RedMentos/Aii/pull/2433.
- Branch: research-perception/v14-speaker-history-nonvoiced-20261123-run4.
- Exact pre-merge head: 9cd05b97f41f32248540a5a91efe359cfd719171.
- PR remains DRAFT / NOT_RELEASED.
- No force-push; next integration uses a normal two-parent merge with the current development base.

## Implemented and tested in this run
- Corrected two assertions in v13/code/tests/test_attention.py: ModulatorPacket uses path_id, as emitted by Neuromod.signal; the tests incorrectly inspected path.
- Commit: 9cd05b97f41f32248540a5a91efe359cfd719171.
- Readback blob: dd4023cb68f4335729d3701106b18a4f56c8e3a1.
- GitHub Actions run 45160985968 (“V14 A4 source-bound attention outcomes”) PASS on CPython 3.13 and 3.14.
- This test validates the real A4 source-outcome → Neuromod packet contract and tampered-source negative path. It does not establish Android or model inference.

## Earlier Perception code carried by PR #2433
The branch also carries the bounded speaker-history correction:
consume_pcm16_voice_window → SpeakerChangeEvidenceRegistry.update → A4 → PerceptPacket/C3 admission.
Only caller-supplied VOICED embeddings enter speaker-reference history. Non-voiced/uncertain frames are source/hash/timestamp checked and suppressed from persistent speaker anchors while remaining eligible for independent RAW EAR/A4 novelty. The impulse fixture asserts IMPULSIVE novelty, no false interrupt, zero accepted speaker frames, DEFER and no persisted embedding vectors. FASTDIAR adapter remains diagnostic-only; no model inference or calibrated identity is claimed.

## Exact tests / environment
- PASS — GitHub Actions run 45160985968: A4 source-bound attention outcomes, Python 3.13 and 3.14.
- PASS — exact earlier focused workflows at prior PR head: RAW EAR consent revocation and public privacy scan; those results are not a substitute for the new merged-base head.
- IN_PROGRESS at last poll — RAW EAR NumPy backend, FASTDIAR adapter, WebRTC/libfvad comparator, prosody-to-attention, Core same-turn, staged/integrated regression.
- LOCAL_LINUX full Aii checkout/pytest: BLOCKED / NOT_RUN; git ls-remote failed because github.com did not resolve and no repository checkout is mounted. No full local compile was run.
- CI is not Android evidence.

## Private device readback
Owner-consented read-only receipts:
- #763 PIPELINE_STATUS: auto-update enabled; installed SHA 8bf44cb50e855a6dba0c91f64f60d8daddcbdc9c; Runtime/Dashboard CI_WAIT; last error NONE.
- #764 DIAGNOSTICS: last stored turn 57.739 s total / 41.627 s TTFT / 38.945 s prefill / 751 prompt tokens / 2 generated tokens; B1/B2 TIME_BUDGET 53.2/54.2 s; 0 valid offers in five-turn aggregate; no native latent exchange proof.
- #765 HEALTH: 1,209 MiB MemAvailable, 1,030 MiB free disk, runtime field unavailable.
- #766 LEARNING_STATUS: unavailable.
- No new user turn, UPDATE_REQUEST, LOG_PAGE, CHAT_SEND, shell, permission/model/weight/data change or device mutation. PR #2433 is not installed.

## Research
- R-084 added to v14/V14_RESEARCH_LEDGER.md: full Nemotron 3 Diarization paper/model-card review; OpenMDW-1.1 weights, 107 MB Q8_0 GGUF, 99.2M parameters, GPU-only reported benchmark; NeMo-Speech.cpp Apache-2.0 runtime lacks documented Android/ARM64 support. sherpa-onnx Apache-2.0 supports Android arm64 but its documented diarization example is offline and uses separate model weights.
- No model or dependency downloaded. No candidate selected. RAW EAR remains primary; diarization remains optional teacher only.

## Integration and next action
- Compare against merge base 8bf44cb50e855a6dba0c91f64f60d8daddcbdc9c: base has 16 changed paths, Perception branch has 16 changed paths, zero overlapping paths. A normal merge can preserve both.
- Merge current base b20e9b1f3dd53af472055adb43da628785494ec4 into the Perception branch with a two-parent commit; rerun exact-head CI on the merged tree.
- Core must rebind the two Perception audio source blobs and dependent recovery/stage/deployer hashes bottom-up; Perception will not edit Core-owned composer files.
- QA should review non-voiced suppression and the impulse consumer regression.
- Redmi audio capture, speaker inference, native latent exchange and Android performance remain REDMI_UNVERIFIED.
- User action: NONE.
