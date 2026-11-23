# V13 current-chain C2 Needle3 pinned native Linux control-call recheck — prereg 2026-10-30

Review-only child of verified #1190 at `bd3cce27d2c009ce44e334503b8e76c1ab5117c1`. Owner: automation. No source, model, catalog, seed, cohort or tool-schema changes.

Run only after C3 Actions `40985573677` and distinct B1/B2 Actions `40985801650` both completed GREEN, respecting serialized native jobs. Current C2 model `Cactus-Compute/needle3`, revision `b274efcb211a9eef48c9a88da4b43bd569696a39`, Apache-2.0, 35,335,380 bytes, SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`. Official native CLI 1,246,880 bytes SHA256 `5eb163c5ed33bd914c103ef8eba2134c7bb2d97bafafdd69f410a4a3100e8c37`. Catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, `select_processing` tool schema blob `954a3f468f10195fbce12d27f68585ee7edee2c9` immutable.

Run the existing `scripts/current_c2_native_linux_smoke_20261028.py` in fresh Linux x86_64 scratch. Prompt `Budget 120 Euro. Berechne die Hälfte.` with bounded tokens/time; require a valid, duplicate-key-free JSON `select_processing` route call from the real pinned model, no external tool execution. Capture complete original raw stdout/stderr, native exit/timeouts, exact artifact hashes, compile/guard tests, privacy/diff, closed ZIP and independent private backup. Any missing artifact is a prerequisite to resolve; do not fake native output.

A GREEN is **C2 native control-call Linux smoke only**, not calibrated C2 accuracy, JEF executive integration, STEP2, B1/B2/C3 combined turn, JEPA, Redmi or Age. Preserve all original negative gates. Exact next command: `PYTHONPATH=v13/code python3 v13/code/scripts/current_c2_native_linux_smoke_20261028.py --scratch-home <fresh> --evidence-dir <fresh>`. Runtime budget UNKNOWN.
