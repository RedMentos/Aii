# Offline World-JEPA fixed-readout action ablation (review-only)

This command compares **observed digital V13 route/outcome** predictions using the existing frozen World-JEPA latent readout, a direct ridge baseline, and two wrong-action heldout controls. It is **not** a real-world causal model, a live V13 organ, a weight-learning permission, a tool controller, or a STEP2/B3/JEPA gate pass.

## Operator prerequisites

1. Stop V13 and any other SQLite writer. Ensure the SQLite file is fully checkpointed and has no `-wal`, `-shm` or `-journal` sidecars. `--ack-closed-store` is only your assertion; it does not stop a process.
2. Keep the database and any report private; do not commit them to public Git. Use the checked-out review branch and a compatible NumPy environment.
3. Confirm that you want this **separate bounded in-memory SHADOW fit** on your own observed digital data. It does not update or persist the live model.

From `v13/code`:

```bash
python -m scripts.world_jepa_closedstore_heldout_action_probe_20261029 \
  --db /private/path/to/closed-v13.sqlite \
  --ack-closed-store --ack-shadow-fit --steps 20
```

`--steps` accepts integers 0..400; zero is a no-training control and **not** learned evidence. The command reads through the existing immutable, SELECT-only SQLite adapter and closes the connection before fitting. It uses the same deterministic train/heldout partition and model seeds as the existing `world_jepa_heldout_action_readout_20261028` probe. A genuine comparison needs a separately registered cohort and appropriate heldout observations; the CLI alone does not supply those.

## Output and interpretation

Only aggregate JSON is printed: canonical parsed-transition source SHA256, train/heldout ID digests, counts, direct ridge MAE, frozen latent-readout MAE, wrong-action MAE and differences for both model seeds. The source digest is **not** a byte hash of the SQLite file; this tool cannot independently prove that the operator's source is a historical, untouched V13 run.

For `gain_vs_direct`, positive means lower pooled MAE than direct ridge on this heldout split. For `gain_vs_heldout_row_mismatch` and `gain_vs_heldout_column_mismatch`, positive means the correctly matched action scored better than that wrong-action control. Neither is proof of causality, independent benefit on new cohorts, native execution or Redmi feasibility. The report always sets `utility_proven=false`, `age_authority=0`, `tool_authority=false` and retains the original negative gates.

On missing acknowledgments, sidecars, symlinks, invalid SQLite or insufficient observations, the CLI returns a sanitized `UNAVAILABLE` JSON and nonzero exit status without echoing paths or private rows. Do not interpret a failed or interrupted run as zero error; preserve the failure separately. No model weights or checkpoint are written.

## Verification and next gate

The repository integration tests use a **synthetic SQLite fixture** and real NumPy fitting/readout, not a real user Store or native model. A future private observed-store run needs closed raw output, source/model/seed pins, independent heldout and negative controls, and an explicit claim limit before any learning/utility gate is reconsidered. The live Age0 runtime remains RECORD_ONLY; STEP2, B3, Body-JEPA, LP3 and jepa_weight remain unchanged.
