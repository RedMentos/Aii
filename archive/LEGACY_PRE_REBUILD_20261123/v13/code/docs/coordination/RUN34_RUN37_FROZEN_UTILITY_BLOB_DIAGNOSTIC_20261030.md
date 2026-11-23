# Run34/Run37 frozen source-preflight root cause — read-only diagnostic 2026-10-30

From unfiltered CI `40975677615` (3372 tests, 2 historical errors): both Run34 and Run37 fail `native_source_or_catalog_changed`. Read-only comparison of `scripts/run34_c3_native_quote_intervention_pilot.py` registered Git blobs against exact current PR #1179 source:

| Frozen input | Registered Git blob | Current Git blob | Match |
| --- | --- | --- | --- |
| `specs/models.json` | `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` | same | YES |
| `scripts/run33_b2_c3_counterfactual_envelopes.py` | `b1d58d7e0c3937787cf15dd801e278de25845879` | same | YES |
| `v13/runners.py` | `efda7aa1aa5729e974d0d641870d4da05d21c961` | same | YES |
| `v13/utility.py` | `f4a92dab9c4a40761d64394cdca1c052e9a76bfd` | `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53` | **NO** |

Both original Git blob objects are retrievable from the remote repository. The newer `utility.py` added finite numeric score/cohort validation and duplicate fixture handling; this is a substantive integrity change, **not** a reason to revert the current source or modify the registered historical hash. Run37 delegates to Run34 prereg, explaining the same two errors. All other registered Run34 source blobs still match.

**Next authorized isolated proof path:** create a disposable historical worktree/source view with the **original** `f4a92...` utility blob and original frozen Run34/Run37 registered source, run their preflight there, retain raw. Keep the current `ff16...` utility and its security improvements in the active review chain. Do not mark the current-source unfiltered suite GREEN or replace original failed evidence. No model/native or phone success is implied by preflight alone.

This diagnostic is read-only; no runtime, model, cohorts, gates or source files changed.
