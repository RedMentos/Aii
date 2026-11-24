# Research & Perception — A3/RAW EYE visual rebase — 2026-11-24

**Started:** 2026-11-24, during run 33  
**Current release base:** `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`  
**New PR:** [#2463](https://github.com/RedMentos/Aii/pull/2463), OPEN / DRAFT / NOT_RELEASED  
**Branch:** `research-perception/v14-vision-current-20261124-run33`  
**Code commit:** `b73ec8a7c7d3d87f0f5d19e41046b62d11496381`  
**Superseded PR:** #2442 CLOSED (not merged); it used the older base `fb563d771fe2d493c4ec25abe94280981d24ef5c`.

## 1. Rebase and scope

The old #2442 branch was 25 commits ahead / 10 behind the current release-development head. Comparing both sides from the old merge base found no overlap between the ten intervening base commits and the twelve changed Perception code/workflow files. A clean current-base commit was therefore created from the current release head with only those twelve reviewed files:

- `.github/workflows/v14-vision-source-lineage.yml`
- `.github/workflows/v14-vision-ui-frame-ingress.yml`
- `v13/code/tests/test_vision.py`
- `v13/code/tests/test_vision_source_lineage.py`
- `v13/code/tests/test_vision_ui_frame_ingress.py`
- `v13/code/tests/test_vision_ui_frame_provider_entrypoint.py`
- `v13/code/v13/vision.py`
- `v13/code/v13/vision_source_lineage.py`
- `v13/code/v13/vision_temporal_adaptation.py`
- `v13/code/v13/vision_temporal_evidence.py`
- `v13/code/v13/vision_ui_frame_ingress.py`
- `v13/code/v13/vision_validation.py`

The stale #2442 board, next-action, and research-ledger snapshots were not copied. #2442 was closed only after the replacement branch existed and its focused CI passed; #2463 now carries the current-base candidate.

## 2. What the code actually does

### A3 vision student/source lineage

- `vision.py` has a learnable ridge-regression projector: standardizes visual features, solves `(XᵀX + λI)W = XᵀY`, normalizes outputs, and atomically saves a hashed `.npz` artifact. This is a real persistent linear student projector, not a neural-network gradient update or full JEPA.
- `train()` records the exact source lineage of its image/caption training set and validates held-out/source-disjoint metrics. `vision_source_lineage.py` invalidates affected or unknown-lineage projectors when a source is forgotten and unlinks the corresponding artifact only after the state update path.
- Text targets use EmbeddingGemma when installed; otherwise `text_encoder()` falls back to deterministic hashed bag-of-words. The LFM2.5-VL-450M teacher is optional and invoked through `llama-mtmd-cli`; it is not loaded by these CI tests. The selected encoder/teacher authority must remain explicit in status and evidence.

### A5 RAW EYE → A4 visual evidence

- `consume_projected_frame_from_provider()` consumes a caller-owned mutable compressed-frame buffer under the exact active `UIObservationLease`.
- It requires a one-shot `ProviderFrameVerifier` issued only by the trusted companion-provider factory after checking the signed receipt and exact frame digest/length. It enforces an 8-MiB buffer cap and 4-million-pixel cap, overwrites the caller-owned buffer, and returns a Percept/A4 admission result.
- The Perception consumer does not open MediaProjection, request Android permissions, store raw frames, persist derived packets, perform OCR, or grant action/learning authority. The Android provider/permission UI is a separate Core/QA dependency.
- Temporal visual evidence is bounded and process-local; provider revocation resets the session history.

## 3. Exact CI evidence — code commit b73ec8a

- Vision source-lineage workflow: PASS, 29 tests on Python 3.13 and 29 on Python 3.14.
- MediaProjection RAW EYE frame-ingress workflow: PASS, 39 tests on Python 3.13 and 39 on Python 3.14.
- These are Linux CI tests of the Perception-side consumer and synthetic provider contracts, not physical MediaProjection capture or Redmi proof.

## 4. Exact staged/integrated blocker

On the same current-base commit:

- `staged-runtime`: FAIL — 19 failed, 234 passed, 10 skipped, 2 errors, 41 subtests passed in 46.93 s.
- `integrated-regression`: FAIL — 1 failed in 0.20 s.
- Root exception in both: `ValueError: unsupported lifecycle source: vision.py`, raised by Core-owned `scripts/source_lifecycle_lock_integration_candidate.py:172`.

The source-lifecycle composer does not yet recognize the new Perception source `vision.py`. The failure propagates into staged Runtime, source recall, JEPA restart, migration, and fair-budget tests. This is not fixed by a Perception-side mock or by bypassing source-forget controls. Core/JEPA must add an explicit reviewed lifecycle mapping for `vision.py` and a source-forget regression; Core/Integrator must then rerun the full staged/integrated suite.

The blocker and exact CI result were posted to Core PR #2462. Perception did not edit the Core-owned composer.

## 5. Research/weight boundary

R-125 records a full read of MobileCLIP2 (arXiv:2508.20691, TMLR 2025 Featured) and a TinyViT audit:

- MobileCLIP2-S0 reports 11.4M image + 63.4M text parameters and 1.5/3.3 ms image/text latency on iPhone 12 Pro Max. These are not Redmi numbers. The official model-weight license restricts use to non-commercial scientific research and excludes product development, so those weights are not accepted for V14's product path.
- TinyViT-5M is a candidate compact A3 feature backbone; its model card lists MIT and Kornia reports TinyViT-5M ONNX export support. It is a classification backbone, not an image-text encoder. Dataset provenance still needs review.
- No model was downloaded or loaded. No user data or images were used.

## 6. Deployment and acceptance

- **Release:** NOT_RELEASED; PR #2463 remains OPEN/DRAFT pending Core lifecycle integration and independent review.
- **Updater:** no update request was sent; no installation receipt exists for this branch.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. No connected handset, MediaProjection capture, Android permission test, UI action, native ARM64 model load, RSS, latency, or thermal test was performed.
- **Canon:** A3 source lineage/projector and A5 RAW EYE→A4 temporal evidence have a focused current-base candidate. The provider/permission layer, integrated Runtime lifecycle, B1/B2/C3, B3 trained latent receiver, and Android device proof remain open.

## 7. Next executable step

Core/JEPA: add the reviewed `vision.py` source-lifecycle mapping and source-forget regression in the Core-owned composer; Core/Integrator: rebind the audio source pins reported on PR #2462. Then run one combined staged/integrated candidate with both audio and vision source paths. After that, verify the actual Android provider under explicit OS permission on authorized hardware. Keep the TinyViT experiment opt-in; no model download or swap without separate explicit user approval.

**User action:** none. No model, permission, data, or installed-app change is requested.
