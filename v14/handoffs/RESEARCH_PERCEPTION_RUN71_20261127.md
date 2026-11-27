# Research & Perception Run 71 — A3 OOD adoption in A5 frame ingress

**Run start:** 2026-11-27 20:23:35 Europe/Berlin. **Completion time:** not independently measured.  
**Owner:** Research & Perception.  
**Repository:** RedMentos/Aii.  
**Branch:** research-perception/v14-a3-tile-ood-abstention-20261127-run70.  
**PR:** https://github.com/RedMentos/Aii/pull/2565 (stacked on #2563).  
**Exact code/test SHA:** 42c78c4ef72ab7d37e0e400bf11748bbadcbb33b.

## Product change

The optional A3 tile-projector OOD gate from Run 70 now reaches the existing A5 MediaProjection frame receiver:
- Versioned Store metadata is validated before loading the optional projector. Legacy gate version 0 remains ungated; unknown/malformed metadata disables only the student estimate.
- Version 1 binds the stored threshold to the loaded projector. Only in-domain tile rows are scored by the A3 projector.
- USED, PARTIAL_OOD, and OUT_OF_DISTRIBUTION states, threshold and exact OOD tile IDs are recorded in the PerceptPacket.
- The global A5 context summary exposes the abstention status. Full OOD abstention does not suppress RAW-EYE features or A4 structural attention.
- No action/learning authority, model, weight, NPZ schema, dependency, microphone permission or persistent user data changed.

## Tests and evidence

**LOCAL_LINUX scratch:** CPython 3.13.5 / NumPy 2.3.5. The helper source compiled. Partial OOD: 8/16 rows scored and 8/16 abstained. Full OOD: 0/16 rows scored. Legacy gate-off: 16/16 rows scored. Invalid threshold controls: 5/5 rejected. This is an isolated helper reproduction, not the full Aii repository suite.

**GitHub-hosted Linux CI:** workflow 46057142216 PASS on Python 3.13 and 3.14. Both jobs compiled the exact RAW-EYE adapter/consumer tests and ran:
python -m pytest -q -s tests/test_vision_ui_frame_ingress.py tests/test_vision_ui_frame_provider_entrypoint.py
Result: 39/39 PASS on Python 3.13 and 39/39 PASS on Python 3.14.
Offline bridge/security workflow 46057142248 PASS. Workflow file: .github/workflows/v14-vision-ui-frame-ingress.yml.

**Full local repository tests:** NOT_RUN / BLOCKED — no mounted Aii checkout; git ls-remote https://github.com/RedMentos/Aii.git failed because GitHub DNS could not resolve.  
**Native model / weight proof:** NOT_RUN.  
**Android / Termux / Redmi:** REDMI_UNVERIFIED; no handset was connected or tested.  
**Deployment:** NOT_RELEASED; no updater or device action.

## Integration blockers

PR #2565 remains NOT_MERGE_READY. The prior shared staged/integrated workflow 46051827046 failed because the Core-owned lifecycle candidate pins vision.py to an obsolete SHA-256. Current vision.py SHA-256 is dcc9bfe87a59313a5b4f9f844ef4ace91fb95112aaab3f53ce5636f50d53429b. Core owns that pin and dependent hashes. Existing Core audio/observer/arithmetic source pins and QA migration PARTIAL-vs-UPDATED assertions also remain unresolved. No new shared staged/integrated run is claimed for this exact head.

The normal Runtime/C3 consumer and Android grant/onStop/revoke/restart/rollback lifecycle are separate Core/QA acceptance work. This PR does not claim that a normal user turn consumed a screen frame.

## Research note

R-190 records the abstract-only ICML 2026 A Geometry-Based View of Mahalanobis OOD Detection and the MIT-licensed OpenOOD-VLM repository check. Its Python 3.8 / PyTorch 1.8.1 / CUDA 10.1 / mmcv / faiss-gpu environment is not a Redmi dependency candidate. The paper abstract cautions that OOD detector behavior is representation-geometry dependent; next experiment is a source-disjoint comparison of diagonal RMS-z, shrinkage covariance and conformal-style calibration. No code or weights were reused.

## Next executable steps

1. Core refreshes the existing vision.py source pin and rebases its normal A5 Runtime/C3 consumer onto the current Perception branch.
2. QA independently verifies Android MediaProjection permission, onStop, revoke, process death, restart and rollback.
3. Perception compares RMS-z, shrinkage covariance and conformal-style calibration on session/app-disjoint UI sources; no default change without false-abstention/missed-OOD evidence.

**User action:** none required. No model, weight, permission, updater setting, device data or installed release was changed.

## Final branch readback

Current PR branch head after the handoff/ledger/workplan/coverage updates: 6f3e87e6c9c946041a95d430b50ad0165bebac7e. Code/test head remains 42c78c4ef72ab7d37e0e400bf11748bbadcbb33b. Documentation-only head passed offline bridge/security workflow 46058233835. PR #2565 still reports mergeable=false and remains NOT_MERGE_READY. No release commit was created.
