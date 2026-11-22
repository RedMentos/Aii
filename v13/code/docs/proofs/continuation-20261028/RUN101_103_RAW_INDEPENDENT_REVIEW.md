# Independent raw review: Run101/102/103 and Run96 RED (2026-10-29)

Owner GPT-6 scheduled continuation. Reviewed actual GitHub Actions run metadata, downloaded **original** artifact ZIP bytes, verified outer GitHub artifact SHA256 digest, ZIP CRC, every inner SHA256SUMS member, exact HEAD and source/compile/privacy/diff exit files. Private Library copies were uploaded and **rematerialized byte-identical**. This is review evidence, not a production merge or gate promotion.

| Run | Exact head / Actions | Original ZIP SHA256 | Closed checks | Result |
| --- | --- | --- | --- | --- |
| Run101 PR #1005 | `c5f0c5154bb27d0a42c7c5a9af170dfec432d316` / `40796198506` artifact `12863464735` | `229e804bd29ed26b9592496ec4b556a440db3595922b420bd6c3b2eb7acffd2a` | CRC clean; 20/20 inner; SOURCE/BASE_INSTALL/COMPILE/INSTALL/NATIVE/FOCUSED/FULL/PRIVACY/DIFF all 0 | **GREEN**. Focused 32 OK, full 2656 OK (1 skipped). Real pinned C3 Linux native two synthetic source answers Dovan=731 Euro and Mira=942 Euro, both `FINAL`, source refs distinct, one native call each and process reaped. Wrong/out-of-scope/conflict/forget controls abstain. |
| Run102 PR #1006 | `5269277a84cfe56a55479510da42ad7146c7fefc` / `40796623840` artifact `12864181918` | `9762cf9392bc626328d4410d2ea281ff7c7725d23592b348b2faeed5fd0711f6` | CRC clean; 15/15 inner; SOURCE/INSTALL/COMPILE/PRIVACY/DIFF 0, FOCUSED=1 FULL=1 | **RED**. Focused 39 FAILED(1), full 2664 FAILED(1; 1 skipped). Test `test_valid_noop_restore_journal_recovered_before_source_read` asserted unchanged SQLite file SHA after normal Store read; actual file hash changed. Preserve failure; do not claim green. |
| Run103 PR #1007 | `b95ef0ccd3f079a600238054a83b422517aedc5e` / `40796986858` artifact `12864895954` | `c4916be506d14b5f8d2d1d60870d4e95271322fdc4e0bf69af27ee8858edea2c` | CRC clean; 15/15 inner; SOURCE/INSTALL/COMPILE/FOCUSED/FULL/PRIVACY/DIFF all 0 | **GREEN**. Focused 39 OK, full 2664 OK (1 skipped). Shared BudgetContext `recover_startup` before `initialize/Store`; invalid path-escape journal, live lock, valid no-op journal, both standalone CLIs tested. No native model in this software run. |
| Run96 PR #1004 | `a915fb92a1968a7712bd858416a329180e17926f` / `40794194803` artifact `12862479183` | `5d01de45308aa2f5a9aba8ad7200f87eba141204215e1dd9366c5a74bfdbe6fa` | CRC clean; 15/15 inner; SOURCE/INSTALL/COMPILE/PRIVACY/DIFF 0, FOCUSED=1 FULL=1 | **RED**. Focused 15 FAILED(1), full 2668 FAILED(1; 1 skipped). Test incorrectly required empty `answer` for a nonfactual CLARIFY question. Run104 #1008 explicitly changes acceptance contract after failure; original Run96 prereg not retroactively satisfied. |

## Source/claim limits
- Run101 is **Linux-native on pinned C3 350M** with public synthetic budget facts, not Redmi, not B1/B2 learning, not general QA. Model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, revision `657e078c94084481950a2d555a941481f715536b`, seed13; model bytes not included in ZIP. No model swap.
- Run103 is the preferred **single shared** candidate over narrower Run102; **do not combine duplicate recovery hooks**. Run103's actual tests prove pre-Store refusal for standalone `scripts.ask_verified_budget` and `scripts.source_exact`. The `python -m v13 source-answer` wrapper still calls `initialize(home)` before `recover_startup(home)` and needs a separate review before any claim that all entrypoints are hardened.
- The original Run96 and Run102 failed attempts remain evidence. A changed test expectation is not an original prereg PASS.
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA unavailable; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole-system incomplete.

## Private durable copies (not public Git)
`/V13-Checkpoints/2026-10-29/Run101-Two-Project-C3/V13_Run101_GREEN_40796198506.zip`
`/V13-Checkpoints/2026-10-29/Run102-Source-Restore-RED/V13_Run102_RED_40796623840.zip`
`/V13-Checkpoints/2026-10-29/Run103-Shared-Restore-GREEN/V13_Run103_GREEN_40796986858.zip`
`/V13-Checkpoints/2026-10-29/Run96-Crosschain-RED/V13_Run96_RED_40794194803.zip`

Next: independently verify Run104 original CI ZIP; if GREEN, execute Run105 preregistered human-entered source -> separate-process real pinned C3 native answer. Separately review the early `v13.__main__.main` initialize/recovery ordering; no premature production merge.
