# Affine action-conditioned JEPA candidate — 2026-10-11

`scripts/action_jepa_objective.py` implements the per-action bias candidate
identified in `CORE_EXPERIMENTS.md`, part 3. The existing WP-T17 benchmark and
its negative utility conclusion remain unchanged. This adjacent candidate is
not registered in the production ObjectiveAdapter or connected to its runtime.

The predictor is `prediction = context · projector · predictor[action] +
bias[action]`. Its trainable parameters are the projector, per-action matrix
and per-action bias. The target is a stop-gradient EMA copy; the original
projector is a geometry anchor. Native model/router parameters are not opened.
Analytic gradients cover every trainable parameter. A bounded global update
norm includes the bias, and the original EMA/variance/anchor treatment is
retained in the adjacent implementation.

The command accepts an immutable JSON dataset with four explicit partitions:
train, calibration, test and retention. All actions need at least two observed
pairs per partition. Episodes and source bytes may not cross partitions, even
through aliases with different source IDs. The encoder and each source must
have a local file path and SHA256; altered source bytes stop the fit. Only the
training rows affect weights and the mean-delta control. The partitions must
be selected before fitting; calibration is evaluated, not used to retune.

Evaluation scores the candidate and controls against one frozen initial
target coordinate system. EMA-space MSE is only diagnostic: moving or
collapsing a target cannot create a passing gain. Both calibration and test
must beat copy, per-action mean delta and a within-action shuffled target by
2% for **every action**. The retention partition separately compares each
action to the initial predictor, allowing no degradation by default.
Noncollapse, finite differences, deterministic repeat, finite values and
checkpoint reload are separate gates. There is an equal-budget no-bias arm.

Input schema (use real observed states and source files for actual experiments):

```json
{
  "schema": "v13-action-jepa-dataset-v1",
  "provenance_kind": "native_dense_tap",
  "bindings": {
    "encoder": {"path": "encoder-binding.json", "sha256": "<SHA256>"},
    "source-001": {"path": "source-001.json", "sha256": "<SHA256>"}
  },
  "rows": [{
    "row_id": "observed-pair-001",
    "episode_id": "original-source-episode-001",
    "source_ids": ["source-001"],
    "partition": "train",
    "action": "summarize",
    "context_state": [0.1, 0.2],
    "future_state": [0.3, 0.4]
  }]
}
```

This sketch does not meet the minimum cohort size. Supported provenance kinds
are `native_dense_tap`, `digital_transition` and `test_fixture`; the last one
always blocks the candidate gate. Checked bytes bind supplied data, while
provenance remains exporter-declared. Actual tap IDs, body/runner revision,
source extraction, observed action and target alignment must be supplied in
the immutable encoder/source files and independently reviewed for real work.

```bash
python3 scripts/action_jepa_objective.py train --dataset DATASET.json --out OUT --dim 16
python3 scripts/action_jepa_objective.py predict --checkpoint OUT/candidate.npz --metrics OUT/metrics.json --states STATES.json --action summarize
```

`predict` reads the measured, hashed checkpoint and uses its actual fitted
matrix and bias. It rejects unknown actions, changed checkpoints and invalid
context dimensions. Outputs are `LOCAL_PREDICTION_HYPOTHESIS`, not observed
future facts. Receiver injection, runtime learning authority and production
integration remain zero/false even if scoped candidate gates eventually pass.
This prototype's retention reference is its initial predictor; retention of
an existing production predictor and its consumer remain separate work.

Software evidence: `docs/proofs/continuation-20261011/action-jepa-software/`
contains ten passing tests (seven new and three existing JEPA checks), two
explicitly synthetic seed-13/21 training runs, immutable inputs, saved weights
and an actual CLI prediction. Both candidate gates fail: a pure constant
action offset has a perfect mean-delta control, so learning cannot establish
utility over that control. The bias does reduce prediction error versus the
no-bias arm in a focused synthetic test; that is implementation evidence,
not a semantic/world quality result. The running 70-case proof's runtime and
harness files were not changed.
