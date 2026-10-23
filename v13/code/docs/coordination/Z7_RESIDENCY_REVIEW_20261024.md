# WP-Z7 residency recovery and measurement review — 2026-10-24

Reviewed `scripts/z7_residency_bench.py` from Claude PR #38 (`cb95905`).
Relevant acceptance scope: §24.14/§24.33 and IH-H6/26/30/33. No architecture,
native model weights, runtime authority or scientific gate is changed.

## Confirmed defects and repairs

- Completed rows existed only in process memory until the entire multi-arm
  run finished. Each completed row is now appended and fsynced before the next
  turn. Atomic attempt state records the binding and completed-row count.
- Reusing an output path could erase a previous or interrupted measurement.
  Every attempt has a unique directory under `<output>.attempts/`. Existing
  evidence blocks an implicit retry; `--new-attempt` explicitly starts a
  separate attempt, preserving earlier rows and final reports. No incomplete
  Runtime state is silently resumed, reconstructed or blended.
- Each attempt binds production Python sources, benchmark dependencies/specs,
  declared installed configuration/model manifests and exact generated tasks.
  A changed binding during collection prevents publication of a final report.
  These are declared model-manifest hashes, **not** verification of model bytes.
- Missing latency and available-memory readings were turned into zero.
  Aggregation now excludes unknown readings and reports sample/missing counts;
  real zero remains a valid reading.
- A turn that became idle before the first polling iteration lost its terminal
  measurement. The collector polls at least once. Status is read from the
  actual assistant message because `audit_event()` has no status field. Only
  FINAL can pass lexical checks; an exceeded budget stops the attempt after
  saving the row. Timing remains a polling upper bound, not exact token timing.
- Direct `/proc/<pid>` reads mixed namespace-local PIDs with an ancestor-mounted
  `/proc`. The existing verified resolver now grounds process identity;
  descendants are mapped back to the current namespace and PID reuse is
  checked. Unavailable readings remain unknown.
- Simultaneous same-named `llama-server` processes collapsed into one reading.
  Rows retain every PID and a separately sampled sum of simultaneous child RSS.
  This is RSS, which can double-count shared pages; no PSS/physical-RAM claim.

## Verification

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest
tests.test_z7_residency_recovery tests.test_handy_pflicht`

The new tests kill an owned subprocess after one durable row, verify that the
row survives and an implicit retry is refused, start a distinct explicit
attempt, preserve an earlier final report, interrupt the next mocked Runtime
turn, change manifest/task bindings, check unknown-versus-zero aggregation,
sample an already-idle terminal turn, reject error status with otherwise
correct text, inspect a real child process through the namespace mapping and
retain two same-executable processes in one simultaneous RSS sample.

All Runtime/model interactions in these checks are mocked; the process-kill
and process-memory checks use real owned Python child processes. This is
software/process evidence, **not** native model utility or Redmi evidence.

## Recovery and remaining limits

After interruption, keep the attempt directory and its `progress.jsonl` and
`state.json`. JSONL rows are authoritative; a kill between row fsync and state
publication can leave the state's count one row behind. A kill during the
current turn may lose that unfinished row, never earlier fsynced rows. Inspect
partial trailing JSONL bytes rather than treating an unfinished attempt as a
complete scientific cohort. The standalone collector refuses automatic reuse;
an intentional new cohort uses `--new-attempt` (the parent package's explicit
`--neu` archives the earlier stage instead).

There is no automatic native rerun, no mid-arm model/KV restoration, no energy
measurement improvement, and no new benchmark decision. Actual Redmi runs,
thermal/energy evidence and canonical gates remain open.
