# Research & Perception handoff — RAW EAR temporal Runtime state, VAD comparison and native libfvad

Date: 2026-11-21 11:53 CET  
Queue: V14-006 / Research & Perception  
Current release-development base: 840a53ab19d0d9609e649f00b25e840465a15bcf  
Branch: research-perception/v14-raw-ear-consent-commit-guard-20261121  
Status: READY_FOR_REVIEW / NOT_RELEASED / REDMI_UNVERIFIED

## Rebase and ownership boundary

The release-development branch is 4a471ae40dd9b768c8130fafdba51900b5417800. This candidate tree is based on that exact base and contains only Research & Perception-owned source, tests, experiments, workflows, its R-023/R-024/R-025 research-ledger append and this handoff. Boss-owned V14 master, Workplan, Coverage Index, Work Board, User Next Action and Boss handoff remain unchanged from the current base.

## Functional changes

1. RAW EAR V3 keeps voiced-frame energy dynamics, F0/voicing, pause-robust voiced energy and activity cues. The default caller path attaches a bounded per-Runtime TemporalVoiceEvidenceRegistry keyed by source/generation; it retains scalar evidence/timestamps only, has a 16-stream LRU bound and explicit reset.
2. First-use get/create/set is guarded by a short module-level lock and a second read. Eight simultaneous first-use callers must all receive the same registry, preventing split temporal history.
3. Consent revocation clears runtime-held and caller-supplied temporal state before later input resumes.
4. The offline comparator reports signed onset/offset delay from the actual smoothed state-changing window, supports libfvad sample-rate retuning, rejects partial 20 ms tails, and keeps WebRTC test-only.
5. Comparator output now uses a generic vad_baseline field. The webrtc_baseline compatibility alias is emitted only for the actual WebRTC wheel backend; libfvad and test EnergyBaseline are no longer mislabeled as WebRTC.
6. The comparator workflow now builds pinned dpirch/libfvad source revision 532ab666c20d3cfda38bca63abbb0f152706c369, runs its native make check suite, installs the shared library and exercises the actual ctypes LibFvadBackend on the synthetic PCM fixture. Exact-head CI is pending.

## Exact source pins

- audio_voice_cues.py: d406e89faf9fc2c62f667a0dcd1fe1d493561d03
- audio_temporal_evidence.py: 098ce2ec6bb0b744166d711a3401b7acf0252de1
- dpirch/libfvad: 532ab666c20d3cfda38bca63abbb0f152706c369 (BSD-3-Clause plus separate WebRTC PATENTS grant)

## Prior exact-head evidence

- RAW EAR → A4 → C3 run 44895732663: PASS, 29/29 on Python 3.11 and 29/29 on Python 3.13.
- VAD comparator run 44895732660: PASS, 7/7 on Python 3.13 and 7/7 on Python 3.14 before the new native build step was added.
- Privacy 44895732546 PASS; model-lab 44895732587 PASS; integration-event 44895732545 PASS; private-bridge push 44895730953 PASS.
- Staged-runtime job in 44895732550 PASS; integrated-regression was still running at last readback.
- Safe-additive 44895732606 FAILs its strict existing-module scope check; manual Boss review is required, with no bypass.
- New native libfvad build/test changes trigger a fresh comparator run; do not carry the earlier 7/7 result forward as evidence for the new native path until the new exact-head run passes.

## Research

R-024 records the full kiloVAD paper (arXiv:2607.25870v1, accepted INTERSPEECH 2026), PulseVAD MIT candidate and dataset/reproducibility caveats, Silero ONNX/30 ms baseline, and why VoxRT's proprietary runtime is not reusable. R-025 records the pinned libfvad native Linux build, BSD-3-Clause plus PATENTS and the new ctypes smoke. No model or weights were downloaded.

## Environment / integration boundaries

- Exact local Aii checkout is BLOCKED because this worker cannot resolve github.com; no local exact-source compile/pytest PASS is claimed.
- The new libfvad build, if green, is NATIVE_LINUX proof only for the pinned shared-library C ABI and synthetic fixture. It is not Android/Bionic or Redmi proof.
- GitHub CI is not local Termux, actual microphone, real speech-corpus accuracy or model-quality evidence.
- Redmi/Termux remains REDMI_UNVERIFIED: no handset connection, microphone consent receipt, installed SHA, updater receipt, CPU/RSS/PSS/battery measurement or deployment.
- No model, weights, runtime, production dependency, Age, permission or user data changed. The CI-built libfvad binary is ephemeral and not committed.
- Core #2158 remains based on an older release ancestor. Source handoff comment 7061363867 supplies both exact source pins and the required full A5→B1/B2→C4→C3 integration tests. It must preserve text PerceptPacket separately from AudioPerceptPacket.
- This remains a caller-supplied PCM16 adapter. Microphone capture, trained VAD, ASR, speech decoder/vocoder, full-duplex, native B1/B2 inference, trained B3 latent coupling and whole-Canon acceptance remain open.
- The V3 producer/comparator surfaces from #2177/#2187 are present here with temporal-state additions. Those older drafts remain open until Boss decides the safe integration path; this PR did not close them.


## Cross-organ research checkpoint — B3 latent acceptance

R-007 in the research ledger is now upgraded from abstract-only to FULLTEXT_REVIEWED for arXiv:2608.16347v2 (2026-11-09). Its key result is not “latent communication works generally”: projection retrieval was 45–50% for three decoder-only pairs, but actual generation-level injection passed the pre-registered test for only Qwen2-0.5B→Phi-3-mini (23.3% vs 0% negative control, FDR p=0.0469, n=30); both Mistral-targeting pairs were null, and the positive trials often produced related-but-wrong answers. The paper explicitly measures transfer of a representational vehicle, not shared meaning, and reports no latency/token savings. It also identifies loss of human-readable monitoring as a risk. The V14 consequence is pair-specific receiver injection plus task-level utility over SOURCE_EXACT/NO_MESSAGE, wrong-source/shuffle/zero-vector controls, semantic correctness, retention, and resource measurements. This strengthens the existing B3 gate; it does not turn B3 ON. Paper-reported code/data availability: Zenodo 10.5281/zenodo.24088479 (MIT code, CC BY 4.0 data/docs); no code, weights or dataset were downloaded.


## llama.cpp latent-path feasibility checkpoint

R-026 in the research ledger records an exact upstream read at llama.cpp `93cb37ea7b5f134cc500b1c5b91d971190600a1a`. The ordinary `/embeddings` endpoint returns per-token final embeddings with `--pooling none`; it is not an arbitrary intermediate-layer API. V13 `v13/code/v13/runners.py` blob `96d91b8aa0d110a7dbcfd438fc8b3b7c504eed9a` confirms `LlamaRunner.tap()` sends token IDs to `/embeddings` with `embd_normalize=-1`, expects one final vector per token, and explicitly records `CAN_LATENT_TAP=True`, `CAN_LATENT_INJECT=False`, `CAN_TRAIN_BODY=False`. The upstream server developer README explicitly says exposing intermediate activations is out of scope because no stable API exists and `eval_callback` is problematic in multi-sequence operation. `llama_batch_ext_set_embd_state` is present but state width is selected only for MTP or LiliCorr-enabled contexts, not general LFM2/Qwen3.5 receiver injection. A MIT third-party SAE patch captures `l_out` and applies same-model control vectors, but the documented architecture patch is Qwen3.5-specific and inherits the multi-sequence risk. Do not reuse it as a production B3 path without a pinned rebase, exact model support, concurrent-sequence tests, Bionic/ARM build, and dynamic receiver-effect proof. The next real B3 step is a model-pair-specific runner extension with an explicit capture layer and receiver injection layer, held-out utility and negative controls; `CAN_LATENT_INJECT` remains false.

## Next

1. Boss performs independent manual review of the non-additive existing-module edit; keep the strict safe-additive failure visible.
2. Core rebinds #2158 to both exact source blobs and proves text + audio PerceptPacket separation and the staged A5→B1/B2→C4→C3 consumer path.
3. QA may request a separate owner-consented Redmi test only after integration/release gates; no current handset receipt or deployment exists. No user action is needed now.


## Latest exact current-head CI — 2026-11-21

Current PR #2192 head `0bba3da8cd57ed808c98f9f79ae2dedcda3647fe`; code-bearing blobs unchanged from the earlier exact code tree.

- RAW EAR → A4 → C3: run `44897542328`, **29/29 PASS** on Python 3.11.18 and 3.13.18; py_compile also PASS.
- RAW EAR vs WebRTC/libfvad: run `44897542315`, on Python 3.13.18 and 3.14.10. Each runner built pinned `dpirch/libfvad@532ab666c20d3cfda38bca63abbb0f152706c369`, native `make check` **13/13 PASS**, then the actual shared-library ctypes + comparator tests **8/8 PASS**.
- Staged context + integrated regression: run `44897542320`: staged-runtime **249 passed / 10 skipped / 47 subtests**; integrated-regression **415 passed / 3 skipped / 58 subtests**.
- Model-lab `44897542295`, public privacy scan `44897542364`, and integration-event/private-bridge `44897553859`: PASS.
- Strict safe-additive `44897553946`: expected FAIL because this PR modifies the existing RAW EAR producer/temporal modules rather than adding only inert modules. The exact log says `path outside inert-module/test/handoff scope`; no validator bypass was used. Manual Boss review is required.
- All above are GitHub-hosted Linux CI, not LOCAL_LINUX or Redmi. Full local checkout remains blocked by GitHub DNS; REDMI_UNVERIFIED / NOT_RELEASED.

## Commit-time consent regression — 2026-11-21

- Added the QA-authored test_consent_revocation_between_pre_and_post_persist_leaves_no_packet regression to this Perception branch. It flips the provider to revoked on the third check and asserts zero persisted PerceptPacket rows and zero A4 telemetry.
- Replaced the separately committed Store.add_packet() call followed by a consent recheck with an audio-owned transaction boundary: validate, insert the packet, then perform the final current-consent check inside the same Store.tx() before COMMIT. A failed check raises and the Store transaction rolls the packet insert back; SQLite readers cannot observe the uncommitted row. Temporal/VAD reset remains fail-closed.
- This serializes the database commit against the final authoritative callback result. A future OS consent provider that can revoke concurrently must make that callback linearizable with its own revocation state; a generic boolean callback cannot make an external OS permission and SQLite one atomic primitive.
- Exact new-commit CI is pending. Full local Aii checkout remains BLOCKED by GitHub DNS; no local repository PASS, microphone, native Silero inference or Redmi proof is claimed.