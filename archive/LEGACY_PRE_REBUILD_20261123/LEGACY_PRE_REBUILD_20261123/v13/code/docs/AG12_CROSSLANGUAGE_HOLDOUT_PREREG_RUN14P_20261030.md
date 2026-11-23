# Run14P — AG12 cross-language historical holdout exclusion (preregistered)

Date UTC: 2026-10-30. Owner: GPT-6 hourly continuation. Review-only child of Run14O PR #1331, exact parent commit `0867211473912e2ca41725579be2c72e710e177d`. No production merge. This package owns only `v13/code/v13/agi/generality.py`, `v13/code/tests/test_ag12_crosslanguage_holdout_run14p.py`, and Run14P-scoped docs/workflow; do not modify other owners' branches or files.

## Existing frozen baseline

- Canon `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Original AG12 `generality.py` blob `0972b10353b8b1911060992f037d0f71eaa05331`; Run14M historical tests blob `e5d33296435e01c59c301dc36e5214939a909c33`.
- English and German StateBoxes `G12_GENERALITY_EVAL` and `G12_GENERALITY_EVAL_DE` remain disjoint, with per-language 32-suite/2048-digest historical registries. This is correct for independent evaluation curves, but `GeneralityEval.guard_training` currently reads only its own language registry, so an English training candidate can include a registered German unseen prompt (and vice versa).

## Test-first expected RED and acceptance

1. Register English seed13 and German seed13; both unseen prompts must be rejected by `guard_training` called from either language, including after Runtime SQLite close/reopen. No cross-language writes, seed/suite changes, or evaluation curve mixing.
2. Register historical German seed17; English `guard_training` must also reject the old German seed13 unseen prompt. Symmetric historical English rotation tested via German guard.
3. Corrupt the other language's union or mark its historical digest recovery unknown; training from the still-healthy language must fail closed (integrity / history unknown), never silently ignore the damaged sibling.
4. If the sibling language StateBox was never created, English-first `guard_training` must still accept unrelated data and reject its own unseen prompt, without creating a German StateBox. The same principle applies to German-first.
5. Keep all original Run14M tests, Run14F/H language/suite tests and AG12→AG9 feedback tests green. `build_suite`, scorer, AG9 feedback, model/source/seed hashes and output authority remain unchanged. The fix is a bounded read-only union of already registered exclusions; it does not preregister unseen tasks in an uncreated language.

Test environment: actual local SQLite Store/Runtime, no native model calls, no external effects. No claim of generalization, training improvement or phone proof. Preserve original failed tests and full-suite historical RED; don't change any acceptance gate.

Negative gates remain: Age0 `RECORD_ONLY`, STEP2 `UTILITY_FAIL`, B3 `NO_PROMOTION`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi unmeasured, V13 incomplete. If focused CI is unavailable, record that explicitly and do not assert GREEN.
