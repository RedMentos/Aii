# World-JEPA offline private SHADOW operator path (review-only)

This is an optional **offline** observed-*digital-outcome* diagnostic. It is not a live V13 organ, a next-physical-world predictor, training resume, proof of utility, tool permission or age promotion. The 400-step registered research cohorts are unchanged; this operator path uses an explicitly separate bounded training run.

## Preconditions
1. Stop V13 and all other writers to its SQLite store; make sure the file is closed and there are **no** `-wal`, `-shm`, or `-journal` sidecars. The `--ack-closed-store` flag records an operator assertion; it does **not** stop a running process.
2. Use a private directory accessible only to the operator, e.g. `umask 077; mkdir -p "$HOME/v13-private"`. Never commit the SQLite database, raw input, fitted NPZ or actual inference output to public Git.
3. Use the exact checked-out review branch, Python/NumPy compatible with the host and an unused checkpoint filename. The script refuses to overwrite.

## Offline observed-store → fitted checkpoint
From `v13/code`:
```bash
python -m scripts.world_jepa_closedstore_private_pipeline \
  --db /private/path/to/closed-v13.sqlite \
  --private-checkpoint "$HOME/v13-private/world-jepa-shadow.npz" \
  --ack-closed-store \
  --steps 20
```
The command emits aggregate JSON with `source_sha256` (hash of canonical parsed observed transitions, **not** a byte hash of the SQLite file), `checkpoint_sha256` (exact fitted private NPZ bytes), row counts, heldout confidence/OOD and label counts. It does not echo action/event IDs, observations, latents or file paths. Keep the output and SHA pins privately. Training uses only the existing deterministic training partition; heldout observations are used for **inference only**.

## Later offline operator inference (no training)
Create a private `probe.json` with exactly two fields:
```json
{
  "observations": [[0.2, 0.5, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]],
  "actions": [[1.0, 0.0, 0.0, 0.0]]
}
```
Those numbers illustrate the **shape**, not a claim that the example state/action is in distribution. Use only genuine compatible observations and one-hot actions from the registered feature schema. Max 128 rows and 256 KiB input; invalid/NaN/boolean/huge values and symlinks are refused.

```bash
python -m scripts.world_jepa_shadow_operator_probe \
  --checkpoint "$HOME/v13-private/world-jepa-shadow.npz" \
  --source-sha256 <EXTERNALLY_RECORDED_64_HEX_SOURCE_DIGEST> \
  --checkpoint-sha256 <EXTERNALLY_RECORDED_64_HEX_CHECKPOINT_DIGEST> \
  --input-json "$HOME/v13-private/probe.json"
```
The CLI outputs predicted *latents*, spread, OOD and bounded confidence. `MODEL_SIMULATION` is **not** a real-world correctness guarantee; `SIMULATION_UNCERTAIN` means insufficient support. Neither label authorizes actions. The checkpoint digest is verified against bytes; the source digest is checked against checkpoint metadata, **not** independently against the original SQLite bytes.

## Failure / continuation
If an interrupted or failed run leaves a private NPZ, preserve it and the failure record; do not overwrite or silently reuse. Create a fresh filename for any new run. Tests are software/synthetic on Linux; no Redmi, live native weights, Body-JEPA learning, B3, STEP2 or whole-system gate has been promoted.
