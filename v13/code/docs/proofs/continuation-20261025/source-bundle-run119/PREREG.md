# Run119 — reproducible V13 source-only ZIP from integrated review chain

2026-10-25 UTC. Parent: Run118 PR #149 head `12130ad6675c94246fe525c5afa5651dc36c988d` (itself based on Run114/Run113/Run112 Claude/Codex chain). Owner: new Run119 GitHub Actions packaging workflow and proof/coordination files only. No runtime/source/model/learning gate edits; no overlap with Run106 `episodes.py`.

## Binding output
- Deterministic `git archive --format=zip` of tracked public source at the exact PR head: root AGENTS, v13 AGENTS, ROADMAP, decisions, complete `v13/blueprint/` and `v13/code/` (including all original code, tests, specs, documentation and existing public evidence).
- No untracked files, no credentials from CI, no HF weights/downloads, no .venv, no native execution. This is **source-only** and is not a claim of a ready trained full V13.
- ZIP integrity: `unzip -t`, required canon/AGENTS/BUILD_STATE/Runtime paths, `sha256sum`, exact `git rev-parse HEAD`, and a non-secret manifest.
- Upload as an immutable GitHub Actions artifact with official pinned `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` (v4.6.2, tag verified through GitHub API), 14-day retention. This **temporary artifact is not the durable backup**; GitHub review branch source, hashes, proofs and BUILD_STATE are the durable checkpoint.
- Official privacy scan, source archive paths allowlisted. If an unexpected sensitive file is detected, fail closed and do not upload.

## Original gates and next
STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE. Run115 LP3 augmented suite FAIL; Run117 confidence selective risk NOT_SUPPORTED. No Redmi/native/full-system proof. After artifact verification, independently review the package, keep building canonical functional gaps and do not treat ZIP creation as completion.
