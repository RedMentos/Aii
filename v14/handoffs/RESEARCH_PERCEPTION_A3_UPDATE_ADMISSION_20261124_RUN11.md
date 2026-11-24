# Research & Perception handoff — A3 update-admission gate and replay research

Date: 2026-11-24
PR: https://github.com/RedMentos/Aii/pull/2463
Base: `gpt6/v13-private-remote-bridge-20261111` @ `8d93236c753f0194224c19edc7411d8d7082b1d6`
Branch: `research-perception/v14-vision-current-20261124-run33`
Code/test SHA: `607d7db7265b69aacb8d7cdc99c63c89992036b2`
Branch documentation head before this handoff: `53d45375d24abfd04a5c018f3fa4ab631128cdc8`

## Concrete runtime change

**Defect:** A3 already computed source-disjoint validation metrics, but the retraining admission path did not consult them. Once an old projector existed, a candidate could pass the old-source replay-retention check even when current examples had no measured source-disjoint generalization above chance.

**Change:**
- Added `_source_disjoint_update_validation()` in `v13/code/v13/vision.py`.
- Both global `train()` and tile `train_tiles()` pass their source-disjoint validation result into `_gate_projector_update()`.
- For an existing projector, replacement now requires a complete measured `SOURCE_DISJOINT` result: every requested fold scored, measurement authority, finite top-1/chance/gain values, and positive held-out gain over chance.
- Missing/partial/non-finite evidence returns `SOURCE_DISJOINT_VALIDATION_UNAVAILABLE`; measured no-gain returns `NO_HELDOUT_UTILITY_GAIN`. The previous artifact remains active and its numeric weights remain unchanged.
- If no previous projector exists, initial LAB_SHADOW_ONLY fitting remains possible; the status records whether source-disjoint utility was measured. This does not promote the projector to a production model or learning organ.
- Passing this admission precondition is not itself proof of semantic truth. Caption targets remain teacher/reference labels; replay-retention scaling still runs after the new-data utility precondition.

## Exact code identity and tests

- Current `vision.py` Git blob: `9f9513043ee36c891556702a1a888a8fd2e2e7f7` at the code update before the final test-only commit; CI SHA-256 of the final exact code: `430071099d5af8d74e37fb6f8c8a1ca2b7aecff1236901e718cb8ea29ef8df96`.
- Current test file Git blob: `c159bf9ad5eaa4f7c4361f9a16f8b15f69ed5b95`.
- Regression covers complete positive evidence, partial folds, non-finite gain, zero gain, and a full train-path negative control that preserves the old artifact's exact SHA and numeric matrix.
- **LOCAL_LINUX / CPython 3.13.5:** isolated execution of the exact admission-helper logic: `py_compile` PASS and 6 admission/negative controls PASS. This is helper-level only, not a full repository test.
- **CI exact code/test SHA 607d7db:**
  - Vision source-lineage workflow #45353124250: `py_compile` PASS; 35/35 tests PASS on Python 3.13 and 35/35 on Python 3.14.
  - MediaProjection RAW EYE ingress #45353124445: PASS on Python 3.13/3.14 (39 tests each).
  - Perception public privacy scan #45353124245: PASS.
  - Runtime deployment integrity #45353124322: PASS.
  - Staged Runtime #45353124273: FAIL, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. The exact root is Core-owned `scripts/source_lifecycle_lock_integration_candidate.py:172` rejecting `vision.py` with `ValueError: unsupported lifecycle source: vision.py`; two migration tests consequently report PARTIAL rather than UPDATED.
  - Core same-turn #45353124220: Python 3.13 failed at the same source-lifecycle composition boundary; Python 3.14 and integrated-regression were still running at the last poll. No overall integration pass is claimed.
- **LOCAL_LINUX full Aii checkout:** BLOCKED / NOT_RUN. No repository checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` fails because github.com DNS cannot resolve.
- **REDMI:** REDMI_UNVERIFIED. No authorized handset/Termux/MediaProjection test was run.

## Whole-system connection and owner boundary

This improves the A3 teacher/reference → student-projector update path and its A5 UI-frame/RAW EYE → A4 consumer. It is not native JEPA, gradient-trained body weights, B1/B2/C3 learning, trained B3 latent coupling, or Android screen capture.

Core/Boss/Integrator must recompose the source-lifecycle builder against the exact current Perception implementation:
1. Replace the obsolete unversioned `VISION_OLD`, `VISION_FORGET_OLD` and `VISION_STATE_OLD` anchor path with a reviewed composition for the atomic/versioned Store-CAS implementation.
2. Pin `vision.py` to CI SHA-256 `430071099d5af8d74e37fb6f8c8a1ca2b7aecff1236901e718cb8ea29ef8df96`.
3. Include `vision_source_lineage.py`, `vision_validation.py` and `vision_ui_frame_ingress.py` in the staged Perception source set.
4. Recompute downstream recovery/stage/deployer source pins bottom-up without relaxing fail-closed checks.
5. QA reruns staged, integrated, same-turn, migration, source-forget, restart and consent-revocation tests on one exact combined SHA.

Perception will not edit the Boss/Core-owned composer or weaken its source pins. The PR remains DRAFT / NOT_RELEASED until the combined chain is independently reviewed and green.

## Research ledger additions R-130–R-132

The branch research ledger appends three full-text reviews dated 2026-11-24:
- **R-130 DLER** (arXiv:2611.04885, 2026-11-03): dual cosine/dot-product replay and advantage-based memory replacement. Public UER README confirms DLER code, but no LICENSE file was found; dependencies pin Torch 1.7.1 / torchvision 0.8.2 and other legacy packages. No import.
- **R-131 SPHERE** (arXiv:2609.33725, 2026-09-27): kernel-smoothed signed prospective loss changes plus entropy-regularized transport. Useful only as a future replay-allocation hypothesis; pairwise/transport overhead grows and no official code/license was found.
- **R-132 CARES** (arXiv:2610.32799, 2026-10-23): frozen-feature, class-aware density-weighted coverage. The paper says code will be released upon publication; very small replay budgets and the need for a suitable frozen encoder are explicit limitations.

These papers do not directly validate the A3 ridge projector. The current change is a bounded source-disjoint utility precondition plus the existing exact replay-retention check. The shared research ledger is append-only; other lanes have parallel R-110–R-129 entries on their own branches. Boss/Integrator must reconcile those entries when composing the shared ledger rather than overwriting another lane's additions.

## User/device state and next action

- No model, weight, permission, installed runtime, phone data or user data changed.
- The latest private device receipt reported `STOPPED_BY_USER`, autostart OFF and model process stopped. No restart, CHAT_SEND, LOG_PAGE or UPDATE_REQUEST was attempted.
- Auto-updater evidence for the installed base does not deploy this PR; this branch is NOT_RELEASED.
- **User action:** none.
- **Next executable Perception step after Core composition:** run the same no-update / uniform-baseline / source-disjoint-update / replay-retention ablation on both global and tile projectors in the composed staged Runtime, including source forget and process restart. Then request a separately authorized Redmi frame/A3 test only when the device is no longer user-stopped.


## Exact follow-up after documentation readback

- Documentation branch head: `bf51f2b477995c217a6aeec5539eda6813b1a973`; executable code/test tree remains at `607d7db7265b69aacb8d7cdc99c63c89992036b2`.
- Re-triggered exact-head CI on the documentation head: vision source-lineage 35/35 PASS on Python 3.13 and 3.14; MediaProjection RAW EYE ingress 39/39 PASS on both; privacy scan PASS; runtime-deployment-integrity PASS.
- Staged-runtime #45353599482: FAIL, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. Root remains `source_lifecycle_lock_integration_candidate.py` rejecting `vision.py` as an unsupported lifecycle source.
- Core same-turn #45353599652: Python 3.13 FAIL at the same source-lifecycle composer; Python 3.14 was still IN_PROGRESS at last poll. Integrated-regression on #45353599482 was still IN_PROGRESS at last poll. No combined integration pass.
- LOCAL_LINUX helper test re-read: CPython 3.13.5, `py_compile` + 6 admission controls PASS. Full repository suite remains NOT_RUN/BLOCKED by no mounted checkout and DNS failure.

**Important limitation:** this gate checks that the current source-disjoint dataset exhibits measured above-chance generalization, then applies the existing old-source replay-retention gate. It does *not yet* report a direct old-projector-versus-candidate performance delta on the same held-out new-source cohort. Therefore it is an update-admission precondition, not proof that the candidate improves the current task. The next Perception ablation must add a same-holdout old-vs-candidate comparison (plus no-update and shuffled-target controls) before any utility claim or promotion.


## Superseding A3 update-admission checkpoint — direct same-holdout baseline added

The earlier limitation about not comparing against the old projector is superseded by the follow-up code at `aa57c9a246caa8d9fd693e149ebedf0d44ac3bf3`.

**New behavior:**
- `vision_validation.source_disjoint_crossval()` now accepts an optional previous-projector predictor and a changed/new-caption evaluation mask.
- For retraining, folds are formed over only new or changed source groups; all other current rows remain available to train each fold. Each fold's candidate is evaluated on its held-out changed/new source rows, and the previous projector is evaluated on those exact same rows.
- An existing projector can be replaced only when the candidate fold models show both above-chance utility and positive held-out top-1 gain over the previous projector, with all folds measured. The existing exact previous-source replay retention/scale gate then runs.
- If there are no new or changed caption rows, retraining is skipped with `NO_NEW_OR_CHANGED_CAPTIONS`; the exact previous artifact is retained. A single changed source is insufficient for source-disjoint update admission.
- This is still a ridge/linear projector experiment in LAB_SHADOW_ONLY. It is not gradient-based neural-weight learning, native JEPA coupling, or production acceptance. The CV candidate is trained on each fold's training partition; it is not a direct before/after measurement of the final full-data candidate.

**Regression evidence:**
- Added a direct source-disjoint test with 12 source groups / 8 changed groups / 4 folds, comparing the fold candidate and prior projector on the same held-out changed-source rows.
- Added no-update, insufficient-source, malformed-baseline, no-held-out-gain, and no-gain-over-baseline controls. Tile retraining with unchanged captions now verifies no-op artifact preservation instead of treating a no-op as an applied update.
- Exact code/test SHA: `aa57c9a246caa8d9fd693e149ebedf0d44ac3bf3`.
- CI vision source-lineage workflow #45355527288: `py_compile` PASS and **36/36 tests PASS** on Python 3.13 and 36/36 on Python 3.14.
- CI SHA-256 pins from the same workflow:
  - `vision.py`: `7be279230d50b8e96199dbc7523813ff1ecab8abce9f77700feaea00bce9e5fc`
  - `vision_source_lineage.py`: `bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f`
  - `vision_validation.py`: `996d53e938942adefac53e461726ad34b1ce78e76e42e6acb6c4f68bde55d59c`
  - `vision_ui_frame_ingress.py`: `8a5d47e0bf4fe51fb5301ed095e69b2d7a8154f185a3168a25cafa244a8f523b`
- **LOCAL_LINUX / CPython 3.13.5:** exact `vision_validation.py` helper copied from the GitHub readback, `py_compile` PASS; synthetic old-vs-candidate, changed-source-mask, no-update, one-source and malformed-baseline controls PASS. A separate 5-case admission-helper control script PASS. This is local synthetic/helper evidence, not a full Aii suite or a native model run.
- Frame ingress workflow #45355527149: PASS on Python 3.13 and 3.14. Privacy scan and runtime-deployment-integrity PASS.
- Staged-runtime #45355527120 and integrated-regression were still IN_PROGRESS at the last poll; Core same-turn #45355527204 had Python 3.13 FAIL at the unchanged source-lifecycle composer and Python 3.14 still running. No combined integration pass is claimed.

The current source-lifecycle composer still needs the exact four-file hashes above. The integration blocker remains Core-owned; Perception did not edit it.


## Final staged/integrated readback for code/test SHA aa57c9a

- Vision source-lineage #45355527288: PASS, 36/36 on Python 3.13 and 36/36 on Python 3.14; exact `vision.py` SHA-256 is `7be279230d50b8e96199dbc7523813ff1ecab8abce9f77700feaea00bce9e5fc`, and `vision_validation.py` is `996d53e938942adefac53e461726ad34b1ce78e76e42e6acb6c4f68bde55d59c`.
- RAW EYE frame ingress #45355527149: PASS on Python 3.13/3.14. Privacy scan and deployment integrity: PASS.
- Staged runtime #45355527120: FAIL, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. All composition failures are `ValueError: unsupported lifecycle source: vision.py` from Boss/Integrator-owned `source_lifecycle_lock_integration_candidate.py`; the two phone-migration tests return PARTIAL instead of UPDATED as a consequence.
- Integrated regression #45355527120: FAIL at the same `unsupported lifecycle source: vision.py` boundary.
- Core same-turn #45355527204: Python 3.13 FAIL (3 failed / 2 passed) at the same source-lifecycle boundary; Python 3.14 remained IN_PROGRESS at last readback.
- This is a composition/allowlist/pin failure, not a focused A3 regression. Do not relax the source hash gate or claim integration. PR #2463 remains DRAFT / NOT_RELEASED; REDMI_UNVERIFIED.
