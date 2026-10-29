# Self/World boolean-numeric corollary attribution — verified software result (2026-10-29)

Owner GPT-6, draft review PR #1085, parent PR #1084 exact `6854e17317e8a7a13bd968ba7a15ea5612c29799`. Binding Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## RED-first and source

- Prospective prereg commit `e293029b1e87ff8f8cc867de24c121b43d3754c5` before tests and implementation.
- Original [RED run 40866385792](https://github.com/RedMentos/Aii/actions/runs/40866385792): 28 focused tests, 8 type-conflict failures/subtest failures (bool↔number wrongly matched as SELF), raw ZIP SHA256 `c926fb58df11583b1366bad6e0a0620157e3421e4b6288ab10d2067cd1e4b69d`, CRC clean, 21/21 hashes, private backup `/V13/RawEvidence/2026-10-29/V13_SELF_BOOL_RED_40866385792_shac926fb58.zip` rematerialized byte-equal.
- Minimal production change: `v13/code/v13/selfmodel.py` Git blob `072ae59d75c97d972433fedd3830002d2c8530ad` (7 additions, 2 deletions). Test blob `3fc2068087861f1e044cd39101addae23cb68634`. Preserve wildcard, numeric tolerance/residual and G-SELF-WORLD-005 cases; bool-vs-number mismatch becomes MIXED with structured residual, not numeric SELF.
- Isolated full-suite CPU torch/transformers dependency repair preregistered; prior original RED not rewritten.

## GREEN

- Exact source-pinned [Actions 40866860307](https://github.com/RedMentos/Aii/actions/runs/40866860307), tested head `52d8acc7b6706a78e1dd5e8fbc46a25e3e24cf3f`, **SUCCESS**.
- **28/28 focused PASS; 3123 full software tests PASS, 11 skipped**. All 9 stage exits SOURCE,VENV,DEPS,PIP_CHECK,FOCUSED,FULL,COMPILE,PRIVACY,DIFF = 0; privacy CLEAN. No native/model calls.
- Original artifact `12894676804`, ZIP SHA256 `d7011c9db572fd5b51a2863db6209a904cbcf50cc4954bd5a0f82da96563517c`, CRC clean, 21/21 SHA256SUMS; privately backed up at `/V13/RawEvidence/2026-10-29/V13_SELF_BOOL_GREEN_40866860307_shad7011c9d.zip`, independently rematerialized byte-equal.

## Limits and next

This is software type integrity in the corollary path, not evidence of native predictive learning, full world model, JEPA, STEP2, B3, Redmi or production integration. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; V13 INCOMPLETE. Next exact command: `gh run view 40867462246 --repo RedMentos/Aii --json status,conclusion,headSha` and independently verify cross-organ Age0 raw, then continue P2 receiver/native or Redmi proof when prerequisites exist. Remaining platform budget UNKNOWN.
