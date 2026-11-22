# Run14G prereg — AG12 language-scoped export isolation (2026-10-30)

Owner: GPT-6 V13 scheduled continuation; review-only child of Run14F PR #1323, immutable parent `22d5cfb1ea8adc4e40374d20ca05386154516751`. Scope: AG12 export file naming only. Canon remains `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`). Existing AG12 module blob `42a06579f8b01ae525b730cd36244e407c7eeef8`.

## Observed defect and acceptance

Run14F isolated German persistent StateBox but `GeneralityEval.run` still unconditionally atomically writes `home/exports/generality-last.json`. A German diagnostic run therefore overwrites the last English evaluation artifact and could be misread as English baseline. No native model or learning evidence supports German capability.

Keep the exact English export path and payload byte-for-byte unchanged. When `lang='de'`, write only `home/exports/generality-last-de.json` with the same existing run/results schema, preserving the language-distinct suite hash. Do not rename English file, migrate historical exports, change scorer, seed, suite, StateBox keys, AG9 calibration, scheduler, operator defaults, native code or weights. Do not allow a German run to alter English last export even on repeated run or restart. `build_suite` already restricts languages to en/de; do not add a third.

Test-first on real `Runtime(home)` SQLite Store: (1) English oracle export exact payload captured, German null export created without changing English bytes; (2) German rerun updates only German export; (3) close/reopen retains English export and both persisted language histories, and new English run leaves German export untouched; (4) no German export exists before first German run; (5) Age0 RECORD_ONLY remains. Existing `tests.test_ag12_language_isolation_run14f` and `tests.test_growth.G12Eval` must remain GREEN.

Run pinned source-only GitHub Actions test-first RED and candidate GREEN with full raw logs, hashes, compile/privacy/diff checks; distinguish test-only proof from native or Redmi evidence. Full-suite historical RED not waived. No STEP2/B3/Body-JEPA/jepa_weight/age/whole-system promotion.

Next: commit isolated regression first and obtain original RED; then patch one-line export selection and obtain candidate GREEN; independently inspect raw and checkpoint. AG9 cross-language calibration and real German learned transfer require separate work.
