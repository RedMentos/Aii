# Run10 post-ablation full software evidence — independently closed 2026-10-29

Review-only checkpoint on child branch `codex/v13-worldmodel-inverse-heldout-baseline-20261029-auto10z` of PR #1139 at `20363b1f3052276254d23878feeb2f92adeff2ca`. No production merge or change to canonical blueprint (Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`).

## Exact completed source and raw
- GitHub Actions run: `40940769318`, workflow `v13-run10-post-ablation-full-20261029.yml`, exact source `a4934736b5c601a546ac999e919183313aeee1dc`, completed `failure` (correctly did not mask failed full suite).
- Original Actions artifact ID `12925954384`, original ZIP SHA256 `ac15ae22bccbc01a33dee5afc9691ceee596129b14e9eb0988845b315824f55d`, 9,732 bytes, ZIP CRC valid, 17/17 inner `SHA256SUMS` valid.
- Independent original raw inspection: `Ran 3262 tests in 248.523s`; **2 ERROR**, **11 skipped**. Both errors are the inherited Run34 and Run37 `native_source_or_catalog_changed` preflight because the historical registered `utility.py` blob differs from current scorer. **No new World-Model ablation regression error**. Do not waive or rewrite those original pins.
- Stage exits: `VENV=0 DEPS=0 PIP_CHECK=0 COMPILE=0 PRIVACY=0 DIFF=0 FULL=1` (two inherited errors).
- Private Library backup: `/V13-Checkpoints/2026-10-29/Automation10-WorldModel-Ablation/RAW_FULL_40940769318_shaAC15AE.zip`, downloaded from GitHub, re-materialized, and byte-for-byte `cmp=0` with original; both SHA256 identical.

## Claim limits and next work
This closes the outstanding PR1139 full-software review, not a full-suite PASS. The World-Model invalid-output ablation consumer fix remains 29/29 focused GREEN in separate run 40940512311. PR1137 separately proved frozen historical Run34/Run37 preflight 11/11 in an isolated original-source worktree, not on current source.

Next independent package: preregistered inverse majority baseline train/heldout leakage witness and candidate repair on this child branch. Keep original frozen source/model/seed/cohort hashes, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi UNMEASURED, V13 INCOMPLETE. No native/causal/Redmi claim.
