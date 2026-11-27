# Research & Perception — Run 72 (2026-11-27)

## Checkpoint

- PR: [#2566 — source-disjoint A3 OOD calibration comparison](https://github.com/RedMentos/Aii/pull/2566), DRAFT / NOT_RELEASED.
- Branch: `research-perception/v14-a3-ood-calibration-20261127-run72`.
- Parent: Perception #2565 at base SHA `b3896e3a3ba5a85de8ea67f45d123ef8e74da075`; #2565 itself is stacked on #2563.
- Code/test commit: `6d0b446a607a42cdbf7f35c6567761e1781703e2`.
- Existing A5 workflow extension: `263b4744bb6f2674caf55366d688da3822c2cd9e`; duplicate standalone workflow removed in `faa25be189b9842a0532c5aeebe3b785bd8ab4ce`.
- The branch has later documentation-only commits; use PR #2566 readback for the final branch head.
- No release commit and no device deployment.

## Implemented

New research-only executable experiment: `v14/experiments/vision_ood_calibration.py`.

- Calls the existing production V13 `vision.boxes` and 37-dimensional `vision.tile_features` functions.
- Compares production diagonal RMS-z, diagonal-shrinkage Mahalanobis (shrinkage 0.25), and source-level split-conformal thresholds for both fixed scores.
- Fit, calibration and test image sources are disjoint. The conformal unit is the maximum tile score per independent image source, so its finite-sample interpretation is source-level and depends on exchangeability; it is not a per-tile conditional guarantee.
- Uses 5 controlled synthetic shifts: black, checkerboard, inversion, random noise and posterization.
- No production threshold, projector metadata, Runtime consumer, model, weight, user image, permission or persistent user data changed.

New tests: `v14/experiments/test_vision_ood_calibration.py` (12 checks). The existing `.github/workflows/v14-a5-visual-frame-bridge.yml` was extended to compile the experiment, run the new tests and execute a one-repeat smoke on Python 3.13/3.14. The duplicate new workflow file was removed so the existing workflow in the parent branch is the PR trigger.

## Exact local evidence

Environment: LOCAL_LINUX scratch, Linux x86_64, CPython 3.13.5, NumPy 2.3.5, Pillow 12.3.0.

- `py_compile`: PASS for the experiment and tests.
- Focused pytest: 12/12 PASS.
- 30-repeat synthetic experiment: PASS; each repeat used 24 fit sources, 20 calibration sources, 20 held-out in-domain sources, 16 tiles/source and 37 features. Fit/calibration/test source IDs were pairwise disjoint.
- Important limitation: no full Aii checkout is mounted locally. The isolated harness used a local mirror of the exact current production `boxes`, `tile_features` and `tile_descriptor_threshold` helper logic. This is not full repository pytest and not hosted CI.
- Exact GitHub CI for PR #2566 was not yet visible at checkpoint; do not attribute parent #2565 CI to this PR.

### Mean source-level rejection over 30 repeats

| Detector / gate | In-domain false rejection | Black | Checker | Invert | Noise | Posterize |
|---|---:|---:|---:|---:|---:|---:|
| RMS-z + production source-disjoint heuristic | 7.33% | 100% | 100% | 100% | 100% | 85.5% |
| RMS-z + source-max conformal, alpha 0.10 | 9.17% | 100% | 100% | 100% | 100% | 85.5% |
| Shrinkage Mahalanobis + source-disjoint heuristic | 16.83% | 100% | 100% | 100% | 100% | 50.83% |
| Shrinkage Mahalanobis + source-max conformal, alpha 0.10 | 10.5% | 100% | 100% | 100% | 92.33% | 36.17% |

Tile-level false-rejection rates were respectively 0.92%, 0.97%, 1.66% and 1.01%. Posterize tile rejection was 22.46%, 23.13%, 8.57% and 5.97%. The script emits all source- and tile-level metrics.

### LOCAL_LINUX scoring microbenchmark

384 training tile rows (37 features) → 16 query tile rows:
- RMS-z: median 0.060 ms, p95 0.0749 ms.
- Shrinkage Mahalanobis: median 0.0961 ms, p95 0.1446 ms.
- Extracting 16 RAW-EYE tile descriptors: median 3.5031 ms, p95 4.8486 ms.
- Raw NumPy feature matrix: 113,664 bytes for 384×37 float64; one 16×37 source is 4,736 bytes.

These are x86_64 scratch measurements only. No ARM/Termux/Redmi performance claim.

## Interpretation

- RMS-z remains the better candidate on this synthetic UI distribution. The current heuristic and source-max conformal RMS-z had identical posterize source rejection (85.5%); conformal's observed in-domain source rejection was 9.17% versus 7.33% for the heuristic.
- Shrinkage Mahalanobis was materially weaker on the near-shift posterization control and slower in this host microbenchmark. This is consistent with the representation-geometry caveat in the ICML 2026 Mahalanobis study; it does not establish that Mahalanobis is universally inferior.
- The source-max conformal threshold offers a clear nominal alpha interpretation for false rejection at the image-source level under exchangeability. It does not guarantee OOD detection and does not imply per-tile conditional coverage.
- Do not replace or retune the production RMS-z threshold from this synthetic result. Keep the current gate shadow/optional; real app/session-disjoint frames are needed before changing defaults.

## Research notes and limits

1. **Janiak, Binkowski & Kajdanowicz, “A Geometry-Based View of Mahalanobis OOD Detection,” ICML 2026, PMLR 306:50747–50778.** Official proceedings metadata and abstract checked; PDF retrieval failed, so this remains abstract-only. The abstract says Mahalanobis performance varies with representation/pretraining/fine-tuning and relates to within-class spectral structure and local intrinsic dimensionality.
2. **Li et al., “SCOPE: Sequential Conformal Probing for Reliable OOD Rejection in LLM Services,” arXiv:2606.21255 (19 June 2026; later arXiv version listed September 2026).** Method and experiment sections in the arXiv HTML were reviewed. It selects a readable hidden layer, calibrates on held-out in-domain examples and uses a sequential e-process. This is a language-model service-boundary method, not a drop-in image detector; no author code or license was verified and no code was reused.
3. **Marques & Berenson, “Local Conformal Calibration of Dynamics Uncertainty from Semantic Images,” arXiv:2605.13028 (13 May 2026), WAFR 2026 workshop page.** The author project page describes observation-conditioned calibration using a learned visual representation, a regression tree and a separate conformal holdout set, evaluated on a simulated double-integrator/Isaac Sim. This supports investigating source/app-conditioned calibration, but it is dynamics uncertainty, not A3 projector OOD classification. No code, weights or datasets were reused.

No third-party implementation, model, weights or dataset was imported. The experiment adds no runtime dependency beyond existing NumPy/Pillow test dependencies.

## Canon and whole-system status

- Relevant Canon path: A3 Student Projector / A5 PerceptPacket / A4 attention-preserving abstention.
- PR #2565's A5 provider→RAW-EYE→optional A3 gate remains WIRED_SYNTHETIC / focused CI evidence only. This experiment does not make it a trained perception model.
- Normal Runtime/C3 consumption remains a Core-owned open dependency. The signed audio consumer still lacks the actual Runtime `audio_window` receiver; QA's visible AudioRecord provider remains OFF.
- B3 native latent coupling, real A3 weight learning, JEPA retention, P0 basic chat and full Android control remain open. Whole-system acceptance is not claimed.

## Device / release boundary

- No fresh authenticated receipt was available for this run. The latest private V13OBS #115 (updated 2026-11-24 09:28:11Z) last reported auto-update enabled and dashboard/runtime UP_TO_DATE at updated_commit `8d93236c753f0194224c19edc7411d8d7082b1d6`; AI runtime STOPPED_BY_USER, model process STOPPED, service/dashboard process RUNNING, autostart false.
- Its last observed turn: 6.295 s total / 2.046 s TTFT / 358 prompt tokens / 7 C3 tokens. B1/B2 native probes ended TIME_BUDGET at 53.2/54.2 s with zero valid offers; native probe SMOKE_PARTIAL. These are historical, not current measurements.
- Newer private V13READ requests were expired/open with no device_status comment: NO_LIVE_RECEIPT. No current installed SHA or updater state is confirmed.
- The last reported 8d932 development-branch commit is 83 commits ahead of the latest integrated release head b20e9 (37/37 CI green); these are distinct references. PR #2566 is not part of either.
- No UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, shell, restart, permission change, microphone capture, MediaProjection capture or device data mutation was performed.
- Android / Termux / Redmi: REDMI_UNVERIFIED. Release: NOT_RELEASED.

## Next concrete work

1. Verify that the exact #2566 Python 3.13/3.14 workflow stays green after any code change; current code/test commit is unchanged since the passing CI run.
2. Core PR #2564 is the active normal-turn UI-frame consumer attempt, but its CI is failing in Core-owned code: run 46061246343 has two operator `:help` dispatch failures; run 46061246219 has two Android UI overlay-anchor failures; staged/integrated run 46061246173 has 16 failures / 250 passes / 10 skips / 2 errors / 48 subtests, including the same overlay mismatch and PARTIAL-vs-UPDATED migration assertions.
3. #2564 currently bases on #2562, while Perception's current A5/A3 provider/preflight chain is #2565/#2563. Core must explicitly reconcile those branches before claiming normal same-turn A5 consumption. The Runtime audio_window receiver remains a separate open gap.
4. QA separately validates the visible MediaProjection/AudioRecord provider's permission grant/denial, onStop/revoke, process death, restart and rollback.
5. Once the visible consented provider exists, Perception repeats calibration on real app/session/version-disjoint UI sources. Consider local conditional calibration only if held-out false-abstention/missed-OOD trade-off improves.
6. P0 basic chat #1904 remains OPEN; this experiment does not repair it. No user action is required now.

## Hosted CI readback — 2026-11-27 20:20Z

Exact PR #2566 head `1c8511f909b171ba85b80145d368cce460cef89d` triggered the existing workflows after the A5 workflow path was extended:

- [Run 46062787585 / workflow #59 — V14 A5 visual frame bridge and A3 OOD calibration](https://github.com/RedMentos/Aii/actions/runs/46062787585): PASS on CPython 3.13.18 and 3.14.10. Each job compiled the production V13 vision/A5 modules plus the experiment, ran `test_vision.py`, `test_a5_visual_frame_bridge.py` and the new OOD tests (**36 passed, 3 subtests passed** on each version), then ran and validated the one-repeat experiment JSON smoke.
- [Run 46062787525 / workflow #590 — V14 MediaProjection RAW EYE frame ingress](https://github.com/RedMentos/Aii/actions/runs/46062787525): PASS on CPython 3.13.18 and 3.14.10, **39 passed** each. This is focused ingress CI, not a device test.
- [Run 46062787616 / workflow #3356 — V13 runtime deployment integrity](https://github.com/RedMentos/Aii/actions/runs/46062787616): offline regression jobs PASS on CPython 3.11.18 and 3.14.10. This does not perform or prove deployment.

The first run is exact child-PR CI for the experiment. The second and third are related workflow checks triggered by the PR update; neither upgrades the device or release state. No Android receipt exists, no deployment was requested, and #2566 remains DRAFT / NOT_RELEASED.
