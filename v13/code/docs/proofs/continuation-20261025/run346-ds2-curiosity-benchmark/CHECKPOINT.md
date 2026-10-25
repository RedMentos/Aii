# Run346 DS2 lab measurement checkpoint — **NOT_SUPPORTED** (2026-10-25)

## Exact evidence and source
- Base Run345 `b9da91da6780b3dc43d3ed3814f205c1b4ada8c7`. Exact evaluated head `226920918d4bcaeb3683dfea949f96c5adce0454`; `sandbox.py` GitHub blob `de203c1cb03901299fec38c340153975e65754b4`, SHA256 `38269668607abf7d2242fe9bd11520b4d5877d8f07a7d58ce49aeb28b0585739`.
- RED Actions `40223066147`, job `121258626525`: 12 tests, 1 failure + 1 error for missing new-kind telemetry. RED ZIP SHA256 `186fefb03c483ed999398debb00de239219b77e59e9df3457e349a59155b93d2`.
- GREEN Actions `40223142601`, job `121258854349`: **12/12 PASS**, privacy CLEAN, frozen paired 20-seed benchmark completed (80 episodes, seeds 401..420, 1200 steps, new kind at 500). ZIP artifact `12609693503` SHA256 `3aed04e2dad9202fe2001f9ab68247f8fc678b3ad1938d1358121025025e7dbd`; raw benchmark JSON SHA256 `ff1363d5b9205da822e9214298e1862a72dde39d5a6fdf8540a5fa03f7767cca`.
- Both ZIPs independently downloaded, CRC and all internal SHA256 manifest entries verified (RED 3/3, GREEN 6/6), embedded HEAD exact. Private Library backups: `/V13/checkpoints/2026-10-25/V13_Run346_DS2_RED_raw_sha186fefb0.zip` and `.../V13_Run346_DS2_NOT_SUPPORTED_raw_sha3aed04e2.zip`.

## Frozen decision
- `lp_goal_novelty` vs `lp`: mean hunger improved by **-0.140885**, noise share -0.01092, learnable KL +0.02194 (all within prereg thresholds).
- But vs `lp_goal`: new-kind final KL **worse** by +0.009315 (required <= -0.05), and improved only **7/20** paired seeds (required >=14). New-kind interactions: combined 103.6 vs `lp_goal` 113.45 and `lp` 122.75. Therefore `NOT_SUPPORTED`; no policy promotion, no post-hoc threshold changes.
- Existing Run110 DS2 historical report also had H2_new_word false; this fresh direct new-kind KL/visit measurement is consistent with that negative finding.
- Code changed only `sandbox.run` telemetry (new-kind interaction count and final KL); no policy/physics/training/runtime changes.

## Next and gates
- A separately preregistered **new policy candidate** could use explicit bounded per-action coverage for newly seen words, with hunger/anti-noise constraints, and a **fresh disjoint** seed cohort. Do not retune on seeds 401..420 or claim improvement without new held-out evidence.
- Lab-only, no native, no Redmi. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, AG6/Redmi MISSING, AG5/STEP8 not promoted, V13 INCOMPLETE. Legacy focused SourceHandoff RED remains independent.
- PR342 targets Run345/PR341, not main. Owner of Run346 files is this branch. Next command: verify remote head, then preregister fresh DS2 candidate or move to another canonical package.
