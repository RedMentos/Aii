# World-Model C5 ActionSelection stage provenance — result (2026-10-29)

## Source and scope
- Review-only child of PR #1146 at `fa71bca01ad5a117b460015ac80d9bbc2ea56857`. No production merge or parent overwrite.
- Producer `v13/focal.py::select` emits `ActionSelection` with `stage=PREDICTION` or `stage=COMMIT`; previous `world_model.transitions` did not distinguish these stages. A provisional selection could become a training label, and one provisional plus one committed packet caused a valid transition to be discarded.
- Tests/prereg committed before source: initial test-only RED head `47dc90fa55b6f28991685a437671b0e32c8cf37e`; added stale-fit witness before source at `3d725c8c78b4236445ac4534f4210824a7a14f78`.
- Source fix `7bcece434622d8701eb8c5bfa184fa221cfe9f23`, Git blob `ed35f24e0d407d38a8750edbc8bbef82fe710192`. Original blob `8d371bdb19faa275c6e17d73ee8745a1b6cf3741`. Canon unchanged blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

## Behavior
- Bounded inspection of up to 16 same-event, same-generation, pre-dispatch C5 packets. At 17 or more, refuse the training row rather than silently choose a truncated subset.
- Explicit PREDICTION rows never become committed training labels; require exactly one COMMIT or legacy unstaged packet. Unknown stage or mismatched packet identity fails closed. Two committed/legacy selections remain ambiguous.
- World-Model revision advanced from v2 to v3: old persisted v2 fits may have learned from provisional packets and are not trusted until refitted from stage-bound observations. No fit objective, heldout split, seed or cohort pin changed. Old registered raw evidence remains immutable.
- Real Store + restart integration and existing World-Model tests are included in focused run. This is software observation integrity, not causal utility.

## Closed evidence
- Initial RED Actions `40955871401`, exact head `47dc90fa55b6f28991685a437671b0e32c8cf37e`: 30 tests / 3 FAIL, raw ZIP SHA256 `ecdac598473123c7abc7dcfdde859aebd1ac49f5292b81e98fb52a773c32ac38`.
- Additional stale-fit RED Actions `40955999349`, exact head `3d725c8c78b4236445ac4534f4210824a7a14f78`: 31 tests / 4 FAIL, raw ZIP SHA256 `42be8a702d49f0140967fd32c3a6fff62a2074842258d709c4bd2db29195cc8c`.
- GREEN Actions `40956045664`, exact head `7bcece434622d8701eb8c5bfa184fa221cfe9f23`: **31/31 PASS**, CANON/VENV/DEPS/PIP_CHECK/FOCUSED/COMPILE/PRIVACY/DIFF exit0, raw ZIP SHA256 `4dae72e526fb5b8e2cd240b9e09b3f30dfcff04ea28d4b38cd85c119f7d36673`.
- All three raw ZIPs CRC clean, 18/18 inner SHA256SUMS, private Library readback byte-exact under `/V13-Checkpoints/2026-10-29/Run10-WorldModelStage/`.
- Independent full suite from parent PR #1146, Actions `40955400194`, remains **RED** (3266 tests, 6 FAIL, 43 ERROR, 28 skipped); its older World-JEPA synthetic fixtures lack the newer event/selection provenance schema, and torch is absent from that isolated CI venv. This stage-focused GREEN does not waive or repair those errors.

## Gates and next
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; V13 INCOMPLETE. No native C3, B1/B2, Redmi, JEPA-weight or whole-system proof.
Next command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_worldmodel_stage_binding_20261029 tests.test_worldmodel_selection_binding_20261029 tests.test_worldmodel_realstore_integration_20261029 tests.test_world_model tests.test_worldmodel_inverse_heldout_baseline_20261029 tests.test_c3_stream_bounds_20261029`.
Next independent package: restore cross-organ World-JEPA synthetic test fixtures by supplying explicit matching events/selection provenance (or keep tests RED where impossible), without weakening the World-Model evidence guard or changing registered cohort arrays.
