# World-JEPA SHADOW private operator inference probe — prereg 2026-10-28

Review-only child of #832 exact `aa0fe52e08f2ea0fc450838bd74e0747ecee0358`; no main merge or owner branch overwrite. This prereg precedes new CLI/test code.

## Authorized capability
An **explicit operator-invoked**, offline, read-only NumPy inference CLI for the existing fitted private World-JEPA checkpoint: `--checkpoint`, externally verified `--source-sha256` and `--checkpoint-sha256`, and a small private JSON input of observations and one-hot actions. It returns only predicted next latents, ensemble spread, OOD and train-bound confidence/labels as a JSON report to stdout. No optimizer/training resume, model downloads, network, Runtime hook, tools, persistent output or age authority.

Require a bounded regular input file (no symlink), duplicate-key/nonfinite refusal, exact observation/action shapes, finite numbers, valid one-hot actions, max 128 rows, no boolean numeric coercion; invalid input must not invoke prediction. Verify external checkpoint pins before inference. Any returned counterfactual is labelled `MODEL_SIMULATION` or `SIMULATION_UNCERTAIN` and is not action permission.

## Test and evidence
Synthetic fitted checkpoint + valid CLI roundtrip equals direct model output, wrong source/checkpoint pins rejected, malformed/oversized/symlink/shape/NaN/action input rejected. Branch-only pinned NumPy CI, raw exits/CRC/SHA, compile, privacy scan. This is software SHADOW utility only, not real file-world/native/Redmi proof. Negative gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. Independent review/full suite required before integration.
