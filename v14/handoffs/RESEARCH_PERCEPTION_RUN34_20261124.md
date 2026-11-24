# Research & Perception — run 34 (2026-11-24)

## Checkpoint

- Started: 2026-11-24 10:00:47 Europe/Berlin.
- Last verified tool checkpoint: 2026-11-24 10:05:55 UTC (11:05:55 Europe/Berlin is **not** inferred; the tool timestamp is UTC). Completion time beyond this checkpoint: UNKNOWN.
- Release-development base read at start: `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Work branch: `research-perception/v14-vision-current-20261124-run33`.
- Code fix commit: `14d6b6338db5e4d965a27bac9a3d7301576496d6`.
- Existing PR: [#2463](https://github.com/RedMentos/Aii/pull/2463), OPEN / DRAFT / NOT_RELEASED.

## Runtime change

The first-frame return from `TemporalVisualEvidence.update()` omitted its top-level `status`, while the ingress consumer reads that field to distinguish baseline warm-up from measured temporal evidence. Added explicit `"status": "WARMUP"` to the first-frame return. The measured path and the existing source/session/consent gates are unchanged. This prevents the first accepted UI frame from raising `KeyError: 'status'` and keeps the first frame from being mislabeled as a measured change.

The existing regression in `tests/test_vision_ui_frame_ingress.py` covers first-frame warm-up, subsequent measured evidence, and the A5→A4 consumer path.

## Exact CI evidence on code commit 14d6b6338db5e4d965a27bac9a3d7301576496d6

- Frame ingress workflow `45361571724`: **39/39 PASS** on Python 3.13 and **39/39 PASS** on Python 3.14.
- Vision source-lineage workflow `45361571677`: **29/29 PASS** on Python 3.13 and **29/29 PASS** on Python 3.14.
- Offline workflow `45361571405`: PASS on Python 3.11 and 3.14.
- Privacy `45361571480`: PASS.
- Offline bridge security `45361563393`: PASS.
- Same-repository integration guard `45361571591`: PASS.
- Staged runtime `45361571653`: **FAIL**, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. Root exception at `source_lifecycle_lock_integration_candidate.py:172`: `ValueError: unsupported lifecycle source: vision.py`.
- Integrated regression `45361571653`: **FAIL**, 1 failure, same unsupported `vision.py` lifecycle source.
- Consumer workflow `45361571596`: Python 3.13 and 3.14 both **FAIL**; 3 failed / 2 passed on Python 3.13, all three blocked by the same source-lifecycle exception.
- The two-checkout migration assertions in the staged suite still report `PARTIAL` rather than `UPDATED`; do not weaken them.

## Integration ownership

No shared lifecycle composer or pin was edited. The Perception branch's current `v13/code/v13/vision.py` Git blob is `3cb25adff1fa917ca87ca00190a70c8c3b838140`; it differs from both the release base and the current Boss integration branch. The Boss branch's composer has its own reviewed `vision.py` pin and obsolete `VISION_*` replacement anchors. Boss/Integrator PR #2443 owns that composer: recompose the current Perception vision implementation and its source-lineage/forget behavior, then rebind all downstream source pins bottom-up. A pin-only substitution is insufficient. No hash check was bypassed and no cross-owner file was changed.

## Research R-117

Added to the branch-local V14 research ledger: Assa et al., *Temporal coding enables hyperacuity in event-based vision*, Nature Communications 17, 9951 (2026-08-20), DOI 10.1038/s41467-026-76878-6. The paper supports a hypothesis that precise event order can carry information lost by time-collapsed frames, but its event-camera timing and deliberately undersampled tiny-image setup do not transfer directly to MediaProjection frames. The upstream code is under a custom non-commercial-only license with no patent grant; no code, data, dependency or weights were imported. Boss must reconcile this branch-local R-117 append with the R-108–R-116 ledger entries already present on the Boss integration branch before final integration.

## Device, release and user boundary

The latest authenticated V13OBS #115 receipt available in the shared issue #1904 is dated 2026-11-24 07:39:27 UTC. It reports installed Runtime/Dashboard SHA `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled, and no updater error. The AI runtime is `STOPPED_BY_USER`, autostart is false, model process is stopped, and native residency is unavailable. Five-turn body-delivery metadata still shows zero valid B1/B2 offers and TIME_BUDGET at 53.2/54.2 s. This is not a new functional test and does not authorize restart or update.

- Candidate #2463: NOT_RELEASED / NOT_INSTALLED.
- Android MediaProjection provider, actual handset frame capture, native model load, Redmi RSS/latency and Android UI action: UNVERIFIED.
- Full local Aii checkout/tests: BLOCKED / NOT_RUN (no repository checkout mounted; container GitHub DNS lookup failed).
- No CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, runtime restart, model/weight/permission change or user-data mutation was performed.
- User action: NONE. Preserve STOPPED_BY_USER; do not send a manual Termux command.

## Next executable step

Boss/Integrator: recompose the exact current `vision.py` and its transactional source-lifecycle/forget consumer into #2443, including a source-forget and restart negative control. Then rerun the exact staged-runtime, integrated-regression, same-turn consumer, two-checkout migration and privacy matrix on the combined head. Only after exact push CI is green should QA consider the already-enabled updater path; a separate authenticated PIPELINE_STATUS is required for installation proof. Perception should then run the timestamp-order versus time-collapsed RAW EYE ablation proposed in R-117 on fixed source/session-disjoint UI fixtures, without importing the upstream code.
