# Run23 immutable evidence inventory and next work

Date: 2026-10-24. Base PR #58 `9fc61a3fce8b69d493edfb2e84e7f4273ba49cc7`. Only isolated patch/test/evidence files are owned by this package.

| File | SHA-256 | Git blob |
|---|---|---|
| LP3_RUN23_LOADER_PREJOIN_GUARD.patch | `269d1a0a4ecc0898d6aefa88826da37d5b818a388f611657df377df8eee26c6c` | `a6fc17b624e52e4225360200b35dd0b99c56a21a` |
| test_lp3_run23_loader_env.py | `2e131f1e7e11637d2c4ef8587a85a005d50e264cfe1346464424f3ec2a7cb24c` | `83eabc998ee8417fd8fe2aaee5c3bf1ee96f58c3` |
| run23-red-targeted-final.log | `ca0dea34b830f6f61a09a7e137fc64923fce329e1b29bcf07e54b6c6525d6b6b` | `2c062b1009f4abcc8ec862583963ae290ab3d5de` |
| run23-green-targeted.log | `a7e4cf4cd0cabbe60fce387768c957e4b10d4c357127dfcb28b514faa28035d1` | `05fc45343a4813d322b83ff29f4e19b41f189eab` |
| run23-postreview-tests.log (inherited intermittent failure) | `f003f17e6276d1649d545807a7d46acc25975a30032ab4d87ea3a7f50b21af92` | `88d8ca555cf15d67d611678eb965de1b411450a5` |
| run23-postreview-rerun.log | `4c3d356a2e51d1c99dd697df7df6f00254cd2f2789eac8764ca87742ad1d5b5e` | `36b84566c2b835a387b63c87fddea0d40aadeede` |
| run23-final-tests.log | `7c8a1d362c85b5c9bb86e615dea0f5c55213023bc668a89fce3c1fa41a50c257` | `0bc318c668336ded0358c12e19b936627f53807d` |

Local standalone LP3-only assembled source+evidence ZIP SHA-256: `a03515a2682461a1dac04e438e1f5cddf6455d8ee545f71248f5f1dd1beb25ce` (superseded after comment-only source correction; final ZIP digest separately reported). The ZIP is a local conversation artifact, not claimed as uploaded to GitHub.

## Remaining independent checks
1. Full current checkout (Claude integration branch, not older main) and official privacy scan; review against all runtime changes, no overlap with another owner's edits.
2. Real delegated writable cgroup-v2: independent `setsid()` negative control, SIGKILL/crash/stale-slot recovery and correct owner locking.
3. Eliminate pre-join ELF constructor window rather than treating the LD_* mitigation as atomic. Evaluate `clone3(CLONE_INTO_CGROUP)` kernel support, seccomp policy and exact launch environment.
4. Recheck seven pinned HF assets, two registered fixture sources, transformers, global owner and measured RAM fit; current host 4 GiB/read-only cgroup is insufficient.
5. Then unchanged LP3 four-seed cohort and separate causal generated-answer utility comparison; preserve original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and incomplete V13.

## Review correction
Patch now covers the comment-only join-helper and launcher corrections. Source blob after patch: cgroup `808acfc9f1f9b9a01311dda29635a7291fffc94a`, launcher `21f0c6952f1c279909157f95750da5154f319a1b`, join helper `1460e89de2f6d9727dbdc0eb22f1c11d4f64bed4`. The intervening inherited SIGTERM test error remains unresolved despite a passing rerun; do not claim stability from one green pass.
