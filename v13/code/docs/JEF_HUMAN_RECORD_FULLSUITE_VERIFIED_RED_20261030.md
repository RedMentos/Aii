# V13 2026-10-30 JEF parent unfiltered full software replay — verified original RED

Review-only branch `codex/v13-jef-record-fullsuite-20261030-auto11u`, exact source parent `5f341acaba4ff37289cde0753448c6b3829f27ec` (PR #1185). Owner: automation; no source modifications. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

Actions **40984606331** exact head `7926e85ee7ebb33d4f9a43d8ad821758c08f686e`: isolated pinned Torch 2.5.1+cpu, Transformers 4.44.2, PEFT 0.13.2, dependencies/pip check/imports all exit0. **Unfiltered 3,395 tests, 11 skips, exactly 2 ERROR**, both historical source-bound preflight refusal `native_source_or_catalog_changed` in `test_run34_c3_native_quote_intervention_pilot` and `test_run37_c3_rule_use_native_pilot`. These tests intentionally pin an earlier frozen native source and cannot be made current-source GREEN by changing their hashes; original RED retained. **No additional errors or failures** on this source snapshot. Compile, privacy CLEAN and diff clean; full suite overall **RED**, not a pass.

Original complete raw artifact **12946014097** ZIP SHA256 `020834f5050b35927b2132844c36a72faf24cf2f82612b7f96a1f9848b7071f1`, CRC clean, 30/30 inner SHA256SUMS. Private Library backup `/V13-Checkpoints/2026-10-30/Run11-JEF-FullSuite/RAW_40984606331_sha020834f5_EXPECTED_RED.zip` independently re-materialized byte-identical.

The newer JEF 512-window and C2 archived validation child PRs #1186/#1187 are **not included** in this full replay; each has its own focused GREEN evidence. Do not claim this is the latest chain's unfiltered result. Next: run one unfiltered replay at the exact latest chain head after heavy native/model jobs are serialized, or prove a bounded changed-test crosscheck; keep the historical frozen Run34/Run37 errors intact. Source, model/seed/cohort hashes, Age 0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 and Body-JEPA negative gates unchanged. No native model or Redmi inference was executed by this suite.

Exact replay command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` with the pinned deps and original source snapshot. Runtime budget UNKNOWN.
