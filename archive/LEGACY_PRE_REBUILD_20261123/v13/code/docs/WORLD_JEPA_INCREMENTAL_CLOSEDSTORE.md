# World-JEPA incremental outcome readout on a closed V13 store (review-only)

This is **not** a live V13 feature or evidence of real-world prediction. It is a separate offline research CLI, combining the read-only local SQLite boundary from draft PR #758 and the unchanged train-only incremental readout from draft PR #764. Source and tests are in draft PR #769. Neither sibling PR is overwritten or production-integrated.

## Prerequisites and command

Stop V13 and all writers; ensure the SQLite file is quiescent and no `-wal`, `-shm` or `-journal` sidecar exists. Make an operator-controlled backup first. Run only on a trusted local machine with adequate CPU/memory; **Redmi thermal/energy cost is unmeasured**.

```bash
cd v13/code
PYTHONPATH=. python scripts/world_jepa_incremental_closedstore.py \
  --db /path/to/closed-v13.sqlite --ack-closed-store
```

Without the acknowledgement or with missing/invalid/insufficient observed rows, the CLI returns a sanitized `UNAVAILABLE` status (exit 2). It never opens the SQLite file writable: `mode=ro&immutable=1`, `query_only=ON`, SELECT-only adapter, no WAL/SHM/journal. It reads existing digital action→outcome rows with recorded outcomes (including unsuccessful actions) and closes the DB before model fitting. **The operator must ensure no writer remains**; the flag is an acknowledgement, not a lock.

## What is measured

At least 32 valid digital action/outcome rows, deterministic split, train-only World-JEPA fitting (seeds 3/7, 400 steps, ensemble3), train-only direct ridge and augmented predicted-latent ridge (lambda 0.01), wrong-action and same-width random projection controls. Only heldout outcomes score the metrics. Report contains aggregate MAE, source/train/heldout SHA256 hashes and explicit non-authority flags; no raw chat text, IDs or database paths. It writes no model weights, database rows or local output files.

The train/heldout split is deterministic by current row order and count, **not** stable across newly appended observations. Compare metrics only for the same source/train/heldout hashes; a new store snapshot is a new cohort and needs its own preregistration.\n\nThis is **digital** action latency/success/output-length prediction, not a physical world model. The original sibling #764 synthetic cohort was negative: direct ridge pooled MAE 0.152555, JEPA-augmented seed3 0.241870, seed7 0.197491. Those results and source/seed/model hashes are preserved, not overwritten by this CLI. The new local SQLite test is synthetic with 0-step diagnostic for I/O, not a 400-step observed-world measurement.

## Gate discipline

No live hook, no Age authority, no jepa_weight promotion, no STEP2/B3/BJ1/LP1/LP2 promotion, no claimed real-user utility, no native/Redmi proof. Independent review, a real closed-store observed run with a preregistered cohort, retention/regression and actual target-device measurements remain open. Review PR #769 before integrating any sibling branch.
