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
provenance remains exporter-declared. For native input the loader also requires
an immutable original tap NPZ and exact context/future row indices; every state
must equal the RMS-normalized original row and its exact original text must be
bound to input/output source bytes. Case/whitespace-normalized text cannot
cross partitions through different native row indices. Digital inputs require a bound
transition record with identical context, action and observed outcome. Actual tap IDs, body/runner revision,
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
contains seventeen passing tests (seven objective, seven export and three existing JEPA checks), two
explicitly synthetic seed-13/21 training runs, immutable inputs, saved weights
and an actual CLI prediction. Both candidate gates fail: a pure constant
action offset has a perfect mean-delta control, so learning cannot establish
utility over that control. The bias does reduce prediction error versus the
no-bias arm in a focused synthetic test; that is implementation evidence,
not a semantic/world quality result. The running 70-case proof's runtime and
harness files were not changed.

## Authentic action-corpus export

`scripts/export_action_jepa_dataset.py` is an offline adapter; it never starts
a model. The authentic restored corpus has **375** sentences and 1,500 C3 text
action outputs. The earlier script's docstring says 376; the checked source
JSON contains 375. The new frozen export plan is
`docs/proofs/continuation-20261011/action-jepa-preregistered-plan-v2.json`.
The earlier exact-text-only v1 plan is retained as superseded evidence. V2
adds NFC/casefold/whitespace source identity before any native tap observation;
cohort counts remain identical.

Its seed-13 historical train-10/test-6 topic split is preserved as historical
metadata. A preregistered seed-20261011 split divides only those ten training
topics into train-6/calibration-2/retention-2. The historical six test topics
remain test topics and are explicitly marked exposed, rather than fresh held
out data. Before reading any taps, the adapter excludes every episode sharing
normalized input or output text across partitions and deduplicates normalized input
episodes. Actual counts: 139 train, 47 calibration, 44 retention and 143 test
episodes; two exclusions; four actions per remaining episode (1,492 pairs).
These are corpus/preparation counts, not measured native results.

Planning preserves the original native ordering: all input sentences, then
all outcomes action by action. Export requires the original finite floating
NPZ `x` (1,875 × 1,024) and its exact `texts` ordering. It also requires a
capture manifest; missing authentic taps or bindings returns `UNAVAILABLE`
without creating a dataset. No test fixture is substituted. The archived
authentic taps have not been found, so actual extraction and native training
remain open until the frozen 70-case proof finishes.

```bash
python3 scripts/export_action_jepa_dataset.py plan --sentences ../bench-results/jepa-ablation-20261010/sentences.json --actions ../bench-results/jepa-action-20261010/actions.json --out NEW_PLAN.json
python3 scripts/export_action_jepa_dataset.py export --plan NEW_PLAN.json --sentences ../bench-results/jepa-ablation-20261010/sentences.json --actions ../bench-results/jepa-action-20261010/actions.json --taps ACTUAL_TAPS.npz --capture-manifest ACTUAL_CAPTURE.json --out EMPTY_EXPORT_DIR
```

The immutable capture manifest schema is `v13-action-native-taps-capture-v1`.
It must declare `native_extraction_observed: true`,
`tap_kind: "llama.cpp-mean-last-layer-embedding"`, exact `plan_sha256`,
`texts_sha256`, `taps_sha256`, `shape` and `dtype`. `artifacts` must bind local
files `model_gguf`, `runner` and the actual original `jepa_ablation_bench.py`
`extractor` with `path` and `sha256`. `runtime_libraries` maps every adjacent
runner `*.so*` filename to its own `path`/`sha256`; export checks both the
declared files and the complete actual inventory. Paths are resolved relative
to the manifest. Source input/output bytes, native cache bytes, original float
indices, encoder bindings and the complete preregistration accompany the
portable exported dataset. Altered arrays, missing libraries, changed corpus,
changed plans and source leakage are rejected. The capture's statement that a
native run occurred remains exporter-declared; file hashes bind evidence and
do not independently certify its origin or provide runtime authority.

## Resumable actual capture and transparent recovery

`scripts/capture_action_jepa_taps.py` adds a real two-thread native server
capture in batches of sixteen. Registration is a separate offline command;
native startup requires a terminal source-intact 70-row STEP2 report. Model,
runner, every adjacent shared library, driver, original extractor, source
JSON, plan and complete text order are immutable resume bindings. A unique
model alias in both `/props` and every actual embedding response identifies
the owned server. Each raw request/response is saved before an atomic NPZ
checkpoint; the checkpoint can be reconstructed and verified against every
original floating-point response. Failed attempts remain separate evidence.

The first actual run captured 384 rows in 24 batches, then its HTTP connection
closed. All 384 rows and raw responses were retained, and the owned worker
was reaped. The original fixed driver did not persist its exit signal, so that
signal is unavailable. A later diagnostic found an 8 GiB cgroup limit and a
historical OOM-kill counter of one; without a starting counter, this cannot be
attributed to that worker. The exact resume initially stopped before any
native startup because the current working tree had progressed beyond the
completed STEP2 source revision.

The unchanged producer now has an explicit read-only outer wrapper:
`scripts/resume_action_jepa_capture_observed.py`. The wrapper verifies all 94
source files against the terminal report using the frozen archive
`step2-webchat-70/frozen-source.tar.gz`, SHA256
`d59ac71c5af559db015e521052f13d00736784ba18eb8c258caf0933d29ee081`.
Only the producer's source-check root points to this immutable snapshot; the
working tree, native protocol, original driver bytes, model and parameters
remain untouched. A separate registration binds wrapper, archive, original
driver, terminal report, all 24 original batch records and the 384-row prefix
array hash. It is a completed historical source-check snapshot, not a claim
that subsequent working-tree changes passed the old STEP2 run.

The observer records actual owned-process `poll`/`wait` return codes, signals,
cleanup requests, cgroup counters before/after and sampled native RSS. Large
model jobs are serialized after the observed memory pressure. These are
concurrent cloud diagnostics; they provide no Redmi or latency-baseline claim.
Two snapshot guards and four capture protocol guards pass without starting
native models. With export, affine, archive and original JEPA tests, the full
software block contains 25 passing tests.

After a complete capture, `scripts/seal_action_jepa_evidence.py` verifies and
seals raw responses into one immutable ZIP. The export JSON stores bound tap
indices instead of duplicating float vectors; loading materializes the exact
RMS-normalized NPZ rows. Deterministic gzip (`mtime=0`) preserves the original
JSON bytes and uncompressed SHA256. A portable metadata ZIP contains exact
source texts, encoder bindings and restoration instructions; the original
15 MiB NPZ is supplied separately. Archive round trips preserve all bytes.
