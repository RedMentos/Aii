# Train-runner proof correction — 2026-10-24

Scope: real isolated NumPy route-head worker with **synthetic** class vectors.
No LLM inference, body update, native embedding collection or Redmi run.

The previous orchestrator could label a partial integration PASS by selecting
only five successful checks and ignoring failed learned-route/F7 checks,
integration return code and lifecycle status. It also inferred forward,
backward and checkpoint interruptions from wall-clock fractions, even when no
kill was observed in the claimed phase. These were proof-acceptance defects.

The corrected proof requires every lifecycle check and successful process exit.
A test-only child observer binds phase markers to the unchanged worker source,
and the parent kills its own disposable child after observing each marker.
Forward/backward markers are at the respective objective statement boundaries
inside the real optimizer; this is not a claim of interruption inside a BLAS
kernel. The checkpoint marker follows a durably flushed partial NPZ write.
Timing-based kills remain supplementary evidence. Production numerical code
and learning permissions are unchanged.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python scripts/train_runner_proof.py \
  --out docs/proofs/continuation-20261024/train-runner/host-software \
  --skip-integration --dim 64 --kills 4
```

Result: `TRAIN_RUNNER_PROOF_PARTIAL_NO_INTEGRATION` (expected exit 1), seven
software checks true; two real-integration checks unknown. Three actual
SIGKILL exits (-9) followed source-bound markers; no killed probe published
metrics, and the checkpoint probe left a partial candidate. Resume j+k equals
the uninterrupted reference; numerical gradient and deterministic repeat pass.
The JSON binds proof/helper/worker/integration sources by full SHA-256.

Memory fields now distinguish the coordinator lifetime peak from sampled test
child memory. Full training-worker peak is explicitly unknown, rather than
misreporting the parent's peak as the worker's. `canonical_gate_pass=false`.

Seven focused regressions pass, including rejection of each missing/false or
non-boolean integration check, failed exit, partial status, stale phase marker,
and preservation of existing final reports. Broader integration belongs to the
coordinator's next checkpoint. No gate is promoted.
