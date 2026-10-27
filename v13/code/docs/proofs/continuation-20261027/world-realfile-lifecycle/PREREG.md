# Prospective real-file-world World-JEPA SHADOW lifecycle — 2026-10-27

Base PR #651 exact SHA `63c00f34ecc41d07c159886ac87fc90998e350d2`. Separate review-only branch, no production merge. Ownership: new `scripts/world_jepa_shadow_lifecycle.py`, new `tests/test_world_jepa_shadow_lifecycle.py`, scoped CI and proofs. Reuse existing unmodified `z12b_world_jepa.py`, `z12c_slot_world_jepa.py`, `world_jepa_slots.py`, `world_jepa_shadow_probe.py`. No registered 201/202/203 data or thresholds changed.

## Problem and functional target
The new read-only inference CLI consumes a persisted v2 checkpoint, but no bound lifecycle presently collects **actual Linux file-world transitions**, trains the independent SHADOW slot model, calibrates on disjoint clean transitions, saves an inference checkpoint, restarts it, and probes a held-out observed transition. Build that isolated offline lifecycle, not a live runtime authority hook. Real file operations occur only in a newly created temporary sandbox directory and use the existing independent world subprocess; never run user file actions, external tools, or paid resources.

## Preregistered execution
A. **Unregistered Z12c ablation smoke**, fresh seed **211**, `--train 600 --cf 12 --attr 16 --steps 50`. This is deliberately too small for original C1–C7 utility acceptance; require process completion, parseable result and both NO_ACTION/SHUFFLED_ACTION metrics (including when FAIL). The original 201/202/203 preregistered measurement is untouched. If smoke fails, preserve raw and investigate; do not relabel as success.

B. **New end-to-end file-world lifecycle**, fresh seed **212**, `--train 600 --steps 50`, all 31 action choices available. Chronological 80% train, final 20% calibration candidates, clean validation excludes overlapping independent-world actions. Verify nonempty coverage of every slot action operation class (including UNTOUCHED). Do not fit on calibration rows. Hash-bind the exact observed cohort rows and exact source-file bytes (including exporter), record training/validation counts and original seed, then save inference-only v2 NPZ with exact provenance. Reload by whole-file SHA256 and provenance, probe one held-out clean row with optional caller-supplied after state, and persist a manifest, provenance, input, probe and checkpoint. All writes only under explicit new output dir. No authority beyond SHADOW.

## Acceptance and negative controls
1. Source and cohort digests are computed from actual bytes/rows, never invented. Manifest and checkpoint hashes match, and checkpoint reload/probe is deterministic after restart.
2. Fit excludes the final 20% chronological calibration partition. Missing clean validation class, nonfinite/invalid data, preexisting output dir or source-digest mismatch fails closed without replacing existing outputs.
3. `after_supplied=true` but `after_verified=false` in probe: a saved observation is caller-supplied and not a causal proof. No training resume, live model change, self-edit, tool/action execution, Age or approval promotion.
4. Synthetic unit tests first (including output collision, missing operation, restart); real file-world Actions smoke afterward, both serialized in one job with original raw stdout/stderr/exit and source SHA256 captured even on failure.
5. Software/synthetic vs actual Linux filesystem/process vs native LLM vs Redmi evidence explicitly separate. Historical full-suite 5 FAIL/73 ERROR remains RED; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, whole V13 incomplete.

Dependencies: existing pinned NumPy and stdlib; no model downloads. Source evidence public only for synthetic content; no private data. Preserve every failed attempt and verify remote bytes/private backups.
