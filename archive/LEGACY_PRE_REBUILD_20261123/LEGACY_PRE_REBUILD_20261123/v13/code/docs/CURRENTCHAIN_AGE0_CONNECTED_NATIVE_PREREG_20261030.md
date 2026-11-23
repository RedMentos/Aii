# V13 current-chain connected Age-0 native vertical preregistration — 2026-10-30

## Immutable parent and scope
Review-only child of PR #1191, parent commit `2895f9a52aded6d7d84846fd79c5664b53eeeff6`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, pinned model catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, control tools blob `954a3f468f10195fbce12d27f68585ee7edee2c9`. No source, model, seed, cohort, or gate edits.

**Question:** On the *same current review chain* after separately successful C3 (#1189), distinct B1/B2 (#1190), and C2 (#1191) Linux-native smokes, does the existing **connected** Age-0 JEF/C2/C3/B1/B2 path still execute and persist correctly? This is a bounded integration check, not a semantic-utility or long-run stability trial.

## Fixed execution plan, prior to CI
1. Ubuntu 24.04 GitHub Actions, fresh isolated venv, `numpy==2.2.6`, `psutil`, `PyYAML`, `Pillow`, `prompt-toolkit==3.0.52`. Pinned `v13.bootstrap` downloads exact catalog artifacts; deep verify all four roles.
2. Serial, non-overlapping native stages on a single fresh home: `v13 probe jef-modes` (C2-only, C3-only, C2+C3, no B manifest), then `v13 probe step12` (persisted JEF/C2/C3 plus distinct B1/B2), then a separate public `v13 ask` to exercise ordinary output. Never run two model-heavy stages concurrently.
3. Validate raw `jef-modes-proof.json` and `step12-proof.json`, native model hash checks, Age0 RECORD_ONLY/system_stage=0, `jepa_weight=0`, `latents_enabled=false`, step1 C2 observed, B1/B2 both observed, separate persisted role states, restart, releases, SQLite integrity and nonempty final ask output. All stage exit codes must be 0; any missing, timeout or malformed proof is RED.
4. Save exact HEAD, model/tool blobs, raw logs, stage exit codes, proof JSON and SHA256SUMS to the original Actions artifact even on failure. No synthetic substitute for native. `public_repo_privacy_scan.py` and `git diff --check` required. No private data or device secrets.

## Preserved negative claims
- Original STEP2 complementarity/utility `UTILITY_FAIL` or `EVIDENCE_NOT_PASSING`; no STEP2_EXIT promotion.
- B3 L1, Body-JEPA utility, `jepa_weight`, age advancement and all §100 acceptance gates remain unchanged.
- This is **Linux CI native**, not Redmi, not measured thermal/battery/RAM retention, not connected real-world task utility or AGI.
- Full unfiltered software suite on #1188 remains RED solely on frozen Run34/Run37 historical source-pin errors (3,395 tests, 2 errors, 11 skipped); do not waive or rewrite those pins.
- If native downloads or runtime fail, preserve all raw negative evidence and continue independent packages.

## Evidence closure
Candidate CI evidence must be independently audited after completion. Do not claim a PASS until the exact remote head, job status, raw ZIP SHA256, CRC, per-file hashes and stage results are checked. Raw artifact may contain private path/metadata: retain in restricted Actions/approved private storage, not public Git.
