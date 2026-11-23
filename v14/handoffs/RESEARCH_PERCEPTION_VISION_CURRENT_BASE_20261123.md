# Perception — current-base A3 source lifecycle + MediaProjection RAW EYE ingress (2026-11-23)

## Scope and base

- Target branch: `gpt6/v13-private-remote-bridge-20261111`
- Verified base SHA at branch creation: `dfa3945b2bbfdb65d932db74e02f402435494e84`
- Perception branch: `research-perception/v14-vision-lifecycle-current-20261123-run18`
- This is a current-base re-composition of the Perception-owned files from the older stacked #2404 candidate. Code/test head `3300aafc0bb27ce22c855596be02cfab1ba027c1` was 10 commits ahead / 0 behind the verified release-development branch. The following handoff correction is documentation-only; no code changed after that tested code head.
- No Core-owned controller guard, recovery/stage/deployer pins, Android companion provider, OS permission, installed model, model weights, user data or release setting was changed.

## Runtime functions added/reconnected

1. **A3 source lineage and compare-and-swap state publication**
   - A3 global and tile projector records now retain exact contributing image source IDs and SHA-256 hashes.
   - A Store-bound versioned snapshot rejects stale writes, preventing a concurrent describe/train/teacher-switch snapshot from overwriting a completed source-forget or ingest.
   - Source forget validates the exact live SourceRef, tombstones the source and invalidates every projector with matching or unknown/legacy lineage. A projector with proven disjoint lineage may remain.
   - Image ingest and last-reference blob cleanup serialize through the Store write transaction. Projector/blob unlink uses descriptor-relative directory opens with O_NOFOLLOW and strict path/name allowlists.
   - Failed or ambiguous source bindings fail closed. This is source-level provenance/invalidation, not proof of neural weight-level unlearning.

2. **A5 MediaProjection frame → RAW EYE → A4/A5 consumer**
   - Adds `vision_ui_frame_ingress.consume_projected_frame`, the one-shot provider verifier factory, `consume_projected_frame_from_provider`, and a scoped source-revocation helper.
   - Requires the exact active UIObservationLease plus a provider-issued one-shot verifier bound to source, capture session, receipt and frame digest/length. Arbitrary callbacks, replay and cross-lease reuse are rejected.
   - Bounds mutable JPEG/PNG input to 8 MiB / 4 MP, derives content-free numeric RAW EYE summaries, uses the existing A3 tile projector read-only when its hash, encoder and live training-source lineage validate, then runs A4 and bounded A5 admission.
   - Provisional frames are not admitted to C3. Raw screenshots and derived packets are not persisted. The caller-owned compressed buffer is overwritten on success and failure. Action, learning and truth authority remain false/zero.
   - The API surface matches the Core provider candidate #2408: its `UIFrameGrant.consume` imports `_issue_provider_frame_verifier` and `consume_projected_frame`; both are present here. The provider/Perception pair is not yet merged or installed.

## Exact files

- `v13/code/v13/vision.py`
- `v13/code/v13/vision_source_lineage.py`
- `v13/code/v13/vision_ui_frame_ingress.py`
- `v13/code/tests/test_vision.py`
- `v13/code/tests/test_vision_source_lineage.py`
- `v13/code/tests/test_vision_ui_frame_ingress.py`
- `v13/code/tests/test_vision_ui_frame_provider_entrypoint.py`
- `.github/workflows/v14-vision-source-lineage.yml`
- `.github/workflows/v14-vision-ui-frame-ingress.yml`

## Verification

- **LOCAL_LINUX / CPython 3.13.5:** copied the exact committed `vision_source_lineage.py` and `test_vision_source_lineage.py` into an isolated temporary package; `pytest -q` = **7 passed**. This covers lineage binding, malformed/unknown lineage, selective invalidation, caption-lineage mismatch, safe unlink, symlink-parent rejection and traversal rejection.
- **LOCAL_LINUX / full Aii checkout:** BLOCKED / NOT_RUN. This worker has no mounted repository checkout and GitHub DNS/network access is unavailable; therefore the full exact-repository vision and ingress suites were not run locally.
- **CI on exact code/test head `3300aafc0bb27ce22c855596be02cfab1ba027c1`:** [vision source-lineage run 45167386005](https://github.com/RedMentos/Aii/actions/runs/45167386005) PASS, Python 3.13 and 3.14; [MediaProjection RAW EYE run 45167386335](https://github.com/RedMentos/Aii/actions/runs/45167386335) PASS, Python 3.13 and 3.14; [privacy scan 45167386073](https://github.com/RedMentos/Aii/actions/runs/45167386073) PASS. **Staged/integrated run 45167386042 FAIL:** 234 passed / 19 failed / 10 skipped / 2 errors in staged-runtime; integrated regression 1 failed. Both fail at the Core-owned `source_lifecycle_lock_integration_candidate.py` pin: `ValueError: unsupported lifecycle source: vision.py`. The current guard expects SHA-256 `758cfc26387bd92da6c1c73d1d53224e76827ba70289c3c9e440f62557c209e5`; this branch's exact `vision.py` SHA-256 is `b42b4ceddc04021b968bbf60940b5346c360903887a8de7b58fc532b800cec2d`. Other new Perception file SHA-256 values: `vision_source_lineage.py` `bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f`; `vision_ui_frame_ingress.py` `4dfde9bc4cde8d555054c353c4636af3d5eb55e24330f2f19f73a6704ece6f0a`. Core owns the pin and dependent recovery/stage/deployer chain; rebind exact hashes bottom-up without weakening the guard. This is a cross-lane integration blocker, not a passing staged consumer.
- **ANDROID / REDMI:** REDMI_UNVERIFIED. No connected handset, Android MediaProjection capture, AudioRecord, Termux runtime, or native performance test was performed.
- **Release/deployment:** NOT_RELEASED. GitHub push is not deployment. No update request or manual Termux command was sent.

## Risks and remaining acceptance

- The A3 projector remains a closed-form ridge/SHADOW artifact, not a gradient-trained JEPA body weight. Source invalidation is not neural weight unlearning.
- RAW EYE features are handcrafted and the tile-projector margin is an uncalibrated student estimate, not OCR/object truth or confidence.
- A real Android companion must verify its signed receipt and hold the same OS-backed UI lease through downstream C3 consumption. Python capability objects are not an OS security boundary.
- Core/QA must integrate the provider and this Perception consumer on one current-base head, verify revocation/zeroization through the complete same-turn Runtime→A5→C3 path, then perform authorized Android instrumentation. No screenshot, derived packet, action authority or learning authority is enabled by this PR.
- The old #2404 branch is stale/diverged (24 ahead / 35 behind the current release base); this branch is the current-base Perception-only re-composition. Do not merge the old stack blindly.

## Next owner actions

1. Perception: read exact-head Python 3.13/3.14 workflows and repair any failures without weakening source/consent pins.
2. Core: rebase its MediaProjection provider onto this current-base Perception API and add one same-turn `UIFrameGrant.consume → RAW EYE → A4/A5` integration test.
3. QA: inspect privacy/revocation/zeroization and Android API-level lifecycle; keep Redmi status unverified until real hardware evidence exists.
4. Boss/Integrator: update the shared work board and Next Action only after independent review; keep the historical Canon unchanged.

**Status:** CODE_PRESENT / WIRED_SYNTHETIC_CANDIDATE / LOCAL_HELPER_TEST_PASS / PERCEPTION_CI_PASS / CORE_STAGED_PIN_FAIL / REDMI_UNVERIFIED / NOT_RELEASED.


## A3 source-disjoint projector validation follow-up — 2026-11-23

Code inspection found a concrete evaluation leak: the previous A3 `crossval()` split region rows, while each image contributes whole-image, half, quadrant and tile-region examples. Rows from the same image could therefore occur in both train and holdout, making the reported retrieval score optimistic.

- Added `vision_validation.source_disjoint_crossval`; global and tile projector training now group every row by its parent image source ID and assign complete source groups to deterministic, row-balanced folds.
- Retrieval uses exact caption-label equivalence, so duplicate captions do not count as false negatives. The chance baseline is computed from the actual held-out label distribution. The luminance decoder is fit only on training sources.
- If only one image source exists, the projector may remain LAB_SHADOW_ONLY but the metrics explicitly return `INSUFFICIENT_SOURCE_GROUPS` and no held-out score. The old row-wise function is retained as `ROW_WISE_DIAGNOSTIC_ONLY`, never used by the production train commands.
- Tile projectors now persist and expose the same source-disjoint validation record. A measured score at/below chance is explicitly `AT_OR_BELOW_CHANCE`; `MEASURED` means the folds were complete, not that utility passed.

**LOCAL_LINUX / CPython 3.13.5 / NumPy 2.3.5:** isolated copy of the helper algorithm and deterministic tests: **5 passed**. The leakage negative control gives row-wise label accuracy 1.00 versus source-disjoint accuracy 0.25 at chance 0.25 (16 sources × 4 region rows); no model/weight was downloaded or changed. This is an isolated helper test, not the full Aii suite.

**CI:** exact-head workflows pending after this commit. Full repository suite remains BLOCKED locally (no checkout; GitHub DNS unavailable). **REDMI_UNVERIFIED / NOT_RELEASED.**

**Core integration pin:** this modifies Perception-owned `vision.py`; Core must recompute its exact SHA-256 lifecycle allowlist and dependent recovery/stage/deployer pins bottom-up. Do not weaken the existing hash guard. New `vision.py` SHA-256: pending exact-byte readback.
