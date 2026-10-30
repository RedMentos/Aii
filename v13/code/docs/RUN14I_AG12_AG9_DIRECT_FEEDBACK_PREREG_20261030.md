# Run14I prereg — AG12 -> AG9 source-bound in-memory feedback (2026-10-30)

Owner GPT-6 V13 continuation. Review-only cross-organ child of Run14H PR #1325 at `5c5d0475ce329f4557bcaf1a517e9e7c41e32557`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Current source blobs: `v13/code/v13/agi/generality.py` `e5e381d129f675f2b9a568660e024dc9f702566c`; `v13/code/v13/agi/solver.py` `aca3973ac45893c217f9319e7251d5c940f2dd8d`. Preserve original English seed13 suite, scorer, model pins, AG9 fit and all age/learning gates.

## Concrete cross-organ bug

`agi.solver.run` executes `growth.eval.run`, then `_feed_metacog` reads `home/exports/generality-last.json` from disk and writes each row into AG9. It does not bind this file to the just-completed run. A stale/tampered/overwritten export can silently contaminate AG9 calibration. After Run14F/G introduced German language-isolated AG12 state and export, the same code always reads the English export, so a German run could feed old English labels to AG9 and misattribute them to the wrong component. Broad `except Exception: pass` hides the defect.

## Acceptance

Keep the public default `GeneralityEval.run` return and on-disk English/German export payloads unchanged. Add an explicit internal opt-in `include_results=False` to return the freshly scored per-item rows only to the in-process caller; no Store or export field `_results` and no prompt text in AG9. `agi.solver.run` opts in, and `_feed_metacog` validates exact current suite hash, completed status, full expected row count/order, finite nonboolean confidence and binary labels before any AG9 write. Never reread the export as feedback source. Preserve English component `ag12:<solver>`; route explicitly German evaluations to separate `ag12:<solver>:de`. No implicit German scheduler/native activation, no change to existing English operator behavior. A bad/partial/missing result must not update AG9.

Test-first real SQLite Runtime and fake in-process body solver (no native/model): (1) mutate export after AG12 finishes but before AG9 feedback; original incorrectly uses forged rows, candidate uses in-memory actual rows; (2) English then explicit German run with different outputs, ensure AG9 components disjoint and English unchanged, German export untouched by feedback; (3) direct incomplete/invalid in-memory rows abstain with no AG9 writes; (4) persisted AG12 run/export omit `_results`; (5) existing Run14F/G/H and G12Eval tests stay GREEN. Tests are synthetic software integrity, not evidence of model utility or German learning.

Capture original RED and candidate GREEN via pinned isolated Actions, compile/privacy/diff and CRC/inner hashes; private Library byte-identical backup. No STEP2/B3/Body-JEPA/jepa_weight/age/Redmi or whole-system promotion; historical full-suite RED retained.

Next: test-first regression and original RED, then minimal source changes in only `agi/generality.py` and `agi/solver.py`, candidate GREEN, independent review and checkpoint.
