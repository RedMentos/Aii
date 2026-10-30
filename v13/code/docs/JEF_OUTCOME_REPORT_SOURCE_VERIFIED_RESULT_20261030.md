# JEF WP-U1 human agreement report exact source — verified 2026-10-30

## Scope and parent
Review-only source candidate from parent `3c9e961d123e5bed1826802fc3e236c19078f5ee`, following prereg `f3d27c73b2d9267368eceb11cbd9aa4395d84f29`. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Only `v13/jefoutcome.py:report` SQL, one dedicated software test file, workflow, and documentation changed. No runtime model, learning authority, cohort, source-pin or age change.

## Original RED
- Test-only head `7db476d5a7cdc7f0dddaadf1fc3e6393c67ab866`, Actions **40987317347 RED**.
- **19 tests, 2 expected failures**, 17 PASS: revoked human source and substituted feedback source still counted as `human_overlap=1` when they should not. Original failure assertions `1 != 0`. All other stages including privacy/diff passed.
- Original raw ZIP artifact **12946864862**, SHA256 `fc40f8963018ddfcc1d480eb027dfebf1b145c79edec0b540aa487c3990e1b17`, CRC clean, **18/18** inner SHA256SUMS.

## Narrow repair and GREEN
- Source candidate `07113fea87f49669ade8194d3422e1705407a507`, `jefoutcome.py` Git blob `132b307270c1c27166a69cefdff7eaf75cfea8ad`. `report` counts only exact matching live `HUMAN_DECISION` source receipts, source hash, decision packet ID, feedback kind/value/permission. Revoked or substituted rows do not inflate overlap/agreement. Self-outcome labels and training policy unchanged.
- Actions **40987423192 GREEN** at exact source head: **19/19 tests PASS**, all **8/8** stages exit0 (CANON, VENV, DEPS, PIP_CHECK, FOCUSED, COMPILE, PRIVACY, DIFF), privacy CLEAN. Includes valid agreement, valid disagreement, revoked source after restart, source substitution, existing JEF human RECORD precedence/window/idempotency and SkillLive route correction.
- Original GREEN raw ZIP artifact **12947088279**, SHA256 `db67c2c5f81b9e15efa5091e48ffa10025b3feb104dffac9aa352b1ec25f9ecc`, CRC clean, **18/18** inner SHA256SUMS.

## Durable raw, claim limits and next
Both original RED and GREEN ZIPs independently downloaded and byte-reverified from private Library:
`/V13-Checkpoints/2026-10-30/Run11-JEF-OutcomeReportSource/`.
No native model or Redmi was executed by this software job. This repairs a telemetry integrity bug; it does **not** establish JEF learning utility, STEP2/B3/Body-JEPA, Age or whole-system completion. The separate native connected Age0 proof on PR #1192 remains independent and intermediate. The unfiltered 3,395-test suite remains RED on frozen Run34/Run37 historical source pins; no waiver.

Owner: V13 hourly automation. Next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_jefoutcome_report_source_20261030 tests.test_jefoutcome tests.test_jef_human_record_precedence_20261030`; then run the unfiltered full software suite on a branch integrating this source with PR #1192, retaining the original historical RED. No auto-merge.
