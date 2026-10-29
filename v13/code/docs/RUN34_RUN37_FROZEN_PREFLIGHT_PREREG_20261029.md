# Run34/Run37 frozen historical source preflight — isolated proof plan

UTC 2026-10-29. Review-only sibling of PR #1136 (C3 native pilot), based on PR #1135 checkpoint `32e6f4846ef03f3d8934f3824f809ff43763a70d`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No production merge or pin rewrite.

## Exact inherited error

Full current-chain software suites fail two historical native prereg tests: Run34 and Run37 raise `native_source_or_catalog_changed`. The registered Run34 cohort binds `v13/code/v13/utility.py` Git blob `f4a92dab9c4a40761d64394cdca1c052e9a76bfd`, whereas the newer integrated production scorer is `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53`. The original scorer exists at public historical commit `a895487f1b8edda600dcd8098cb7f6a92bfbecfa`. The current scorer's safeguards are legitimate and must remain intact. Do **not** update registered cohort hashes or relabel the current-source failures as passes.

## Paired software-only test

1. In a fresh checkout of current review branch, run `test_run34_c3_native_quote_intervention_pilot` and `test_run37_c3_rule_use_native_pilot` with current utility.py. Retain original RED; explicitly check the two named source-pin errors.
2. In a **separate local temporary Git worktree** of the same exact review HEAD, replace **only** the local utility.py bytes with `git show a895487...:v13/code/v13/utility.py`. Verify its blob is `f4a92dab...`, current original is `ff16ab...`, and every other Run34 registered source pin remains exact. Run the same tests; do not modify GitHub production source or source pins.
3. Preserve raw, SHA256SUMS, exit codes, exact branch head and source blobs. A GREEN frozen preflight proves only the registered historical **software prereg** is reproducible. It is not native inference, a new Run34/Run37 outcome, STEP2 utility, or V13 completion. A failed frozen preflight remains RED evidence; do not weaken assertions.
4. No paid provisioning, no model download, no private data, no native execution. Do not copy the frozen scorer back to current code.

Owned files: `.github/workflows/v13-run34-run37-frozen-preflight-20261029.yml`, this prereg, dedicated BUILD_STATE. Other source untouched. Exact next command: inspect Actions result, CRC/SHA256SUMS, private backup and review-only PR.
