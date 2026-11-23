# Run14H prereg — AG12 same-language suite identity containment (2026-10-30)

Owner GPT-6 V13 continuation. Review-only child of Run14G PR #1324 at `658dd1b6caf8eeed44e808973df66a5023c0af7b`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; candidate parent AG12 module blob `2b65c8f4b9a63a9207412e4939ac121c4124d9a4`. No modification to the original English seed13 cohort, suite, scorer, source/model hashes or existing negative evidence.

## Observed failure

AG12 persists `runs` in a language-specific StateBox and records `suite_hash` on each run, but after an operator constructs a different seed of the *same language*, `due()`, `curve()` and `report()` still use all historical runs without filtering `suite_hash`. New suite is incorrectly marked not due, old curves can be mistaken for new generalization. Two live instances of different seeds sharing one language key can also misuse `guard_training`: it reads the active Store holdout but the stale instance's own prompts, permitting incorrect holdout admission; `run` could mix records after a rotation. This is an integrity defect, not an AG12 utility measurement.

## Fixed acceptance and limits

Retain exact StateBox keys (English `G12_GENERALITY_EVAL`, German `G12_GENERALITY_EVAL_DE`), `REVISION`, original suite hash, seed13 task content, original raw run history and last export file paths. Scope `due`, `curve` and report's runs/last/solvers to current `suite_hash` only; raw historical runs remain untouched in Store for audit. Before using a stale evaluator instance for `guard_training`, `practice_items`, `due`, `run`, `curve`, or `report`, reject with a clear deterministic error. Check active suite identity inside `run`'s optimistic Store mutation too, so an in-flight seed rotation cannot write stale run/export. No new implicit evaluation, learning, scheduler, native, model or Age authority.

Test-first real SQLite Runtime: seed13 English oracle run; construct seed17 English on same Store, verify due=True, curve empty, report 0 current runs but historical raw run retained; seed17 run then correct new curve; stale seed13 guard_training, run and read methods fail closed. Repeat for German seed variants, verify language isolation, unchanged English export, and restart. Existing Run14F/Run14G and G12Eval tests remain green.

Collect exact-source original RED and candidate GREEN via isolated pinned GitHub Actions, privacy/compile/diff, original raw ZIP hashes and private Library readback. All tests are software-only. No STEP2/B3/Body-JEPA/jepa_weight/Redmi/age/whole-system promotion; historical full-suite RED remains.

Next: commit regression first, verify original RED, patch current-suite filtering and stale-instance containment, verify candidate GREEN, independently review and checkpoint.
