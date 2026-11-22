# World-JEPA digital outcome SHADOW — offline closed-store audit

**Not a live feature.** This candidate reads existing V13 **finalized digital action/outcome** records from a closed local SQLite store, evaluates the already implemented World-JEPA adapter against direct ridge and train-mean controls, and prints aggregate JSON only. It does **not** predict exogenous future-world state, send messages, modify the DB, persist weights, change permissions, or prove real-world causal utility.

From `v13/code` with NumPy installed, **stop V13 first** and ensure SQLite is checkpointed and no `-wal`, `-shm` or `-journal` sidecar exists:

```sh
PYTHONPATH=. python scripts/world_jepa_readonly_store.py --db /path/to/closed-v13.sqlite --ack-closed-store
```

The runner rejects symlinks, missing files, sidecars and malformed/insufficient transition tables. It opens `mode=ro&immutable=1`, enables `PRAGMA query_only=ON`, and exposes only SELECT methods to `world_model.transitions`. It reads at most the existing 2048-transition cap, never prints raw action IDs or chat text and never creates an output file. Redirect stdout to a **private** file only if you intend to keep the aggregate report. Do not publish local raw data or path. A running database with uncheckpointed WAL is unsafe for immutable reads; do not bypass the sidecar refusal.

The 2026-10-27 synthetic-only PR #754 control was **negative for incremental utility**: direct ridge pooled MAE 0.152555 vs World-JEPA readout 0.203321/0.192621 (two seeds), although both beat wrong-action. This command permits a future real observed-store check; its software tests use only a synthetic temporary SQLite database and `STEPS=0` (not the preregistered 400-step evaluation). Genuine local results must be privately preserved and reviewed separately before any integration.

All LP1/LP2/BJ1/STEP2/B3 negative gates, jepa_weight0, Age authority0, Redmi unmeasured and whole V13 incomplete remain.
