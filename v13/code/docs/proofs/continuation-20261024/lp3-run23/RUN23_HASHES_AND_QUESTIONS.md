# Run23 immutable evidence inventory and next work

Date: 2026-10-24. Base PR #58 `9fc61a3fce8b69d493edfb2e84e7f4273ba49cc7`. Only isolated patch/test/evidence files are owned by this package.

| File | SHA-256 | Git blob |
|---|---|---|
| LP3_RUN23_LOADER_PREJOIN_GUARD.patch | `084020d010f2f77f90f98726a932fa762417d6129b75f3f710893da1e9909af6` | `d1a63d24886b9d69a0e1cf2c7499b1f9d274424c` |
| test_lp3_run23_loader_env.py | `2e131f1e7e11637d2c4ef8587a85a005d50e264cfe1346464424f3ec2a7cb24c` | `83eabc998ee8417fd8fe2aaee5c3bf1ee96f58c3` |
| run23-red-targeted-final.log | `ca0dea34b830f6f61a09a7e137fc64923fce329e1b29bcf07e54b6c6525d6b6b` | `2c062b1009f4abcc8ec862583963ae290ab3d5de` |
| run23-green-targeted.log | `a7e4cf4cd0cabbe60fce387768c957e4b10d4c357127dfcb28b514faa28035d1` | `05fc45343a4813d322b83ff29f4e19b41f189eab` |
| run23-final-tests.log | `7c8a1d362c85b5c9bb86e615dea0f5c55213023bc668a89fce3c1fa41a50c257` | `0bc318c668336ded0358c12e19b936627f53807d` |

Local standalone LP3-only assembled source+evidence ZIP SHA-256: `2bee86f395b2d60a70e9c17420d9c3087f7fe647ade8aee4cf326d1cc9d75cee`. The ZIP is a local conversation artifact, not claimed as uploaded to GitHub.

## Remaining independent checks
1. Full current checkout (Claude integration branch, not older main) and official privacy scan; review against all runtime changes, no overlap with another owner's edits.
2. Real delegated writable cgroup-v2: independent `setsid()` negative control, SIGKILL/crash/stale-slot recovery and correct owner locking.
3. Eliminate pre-join ELF constructor window rather than treating the LD_* mitigation as atomic. Evaluate `clone3(CLONE_INTO_CGROUP)` kernel support, seccomp policy and exact launch environment.
4. Recheck seven pinned HF assets, two registered fixture sources, transformers, global owner and measured RAM fit; current host 4 GiB/read-only cgroup is insufficient.
5. Then unchanged LP3 four-seed cohort and separate causal generated-answer utility comparison; preserve original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and incomplete V13.
