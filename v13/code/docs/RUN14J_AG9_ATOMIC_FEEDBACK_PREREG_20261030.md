# Run14J prereg — atomic idempotent AG12→AG9 feedback (2026-10-30)

Owner GPT-6 V13 continuation. Review-only cross-organ child of Run14I PR #1326 at `57cfd814fdbbdedf5e266ae57388a1be91def92a`. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Source owners: `agi/metacog.py` `658b3c04bd95907211d1f5f7601436d3370d68e1`, `agi/generality.py` `e0daa99e5953caeba49a1167cfbbbc5885a7522f`, `agi/solver.py` `1e7d8dce2790c908dd294f3c3680dbab519adc10`. Preserve English seed13 suite/scorer, AG9 PAV/calibration, model hashes, negative gates.

## Observed defect

Run14I now feeds exactly validated in-process AG12 rows to AG9, but `_feed_metacog` still calls `Metacognition.record` 88 times. Each row causes a separate optimistic Store mutation and refit. A SQLite failure midway leaves a biased partial batch, and repeating feedback for one completed run duplicates all rows. This is a concrete persistent learning-signal integrity and phone-write-amplification problem, not an AGI claim.

## Fixed acceptance

Add opt-in `Metacognition.record_batch(component,pairs,receipt)` that validates the full nonempty bounded batch (finite nonboolean confidence, exact binary outcome, valid component and bounded opaque receipt) *before* any Store mutation. Append the entire batch, fit existing unchanged PAV exactly once, and save one optimistic StateBox mutation; a failed Store write leaves no partial batch. Record a bounded `RECEIPT_HISTORY` (at least 120, no unlimited growth) per component; repeating the same receipt within retention must not add samples. Existing `record`, calibrator, `MIN_SUPPORT`, `WINDOW`, and default behavior remain unchanged. Dedup is explicitly bounded, **not** a global permanent exactly-once guarantee.

For AG12 direct in-process `include_results=True`, return a fresh ephemeral feedback nonce (never persist/export it), bind nonce + suite hash + exact ordered rows to an opaque receipt in `agi/solver.py`, and use `record_batch` once. No prompt text enters AG9. Missing/invalid nonce or rows means no AG9 write. English component `ag12:<solver>` unchanged; German `:de` isolated. No implicit German/native/learning activation.

Test-first real Runtime SQLite and fake solver: 88 AG12 rows produce one Store mutation and unchanged calibrator math; duplicate feedback of the exact same run is idempotent; different runs are not deduped; injected SQLite write failure leaves AG9 state untouched; invalid batch/receipt never writes; `_feedback_nonce` and `_results` absent from persisted AG12 run and both export files. Existing AG9/AG12/solver tests must stay GREEN.

Collect pinned original RED and candidate GREEN raw ZIP with CRC/inner hashes, compile/privacy/diff and private Library byte-identical backup. No Age/STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole-system promotion; historical full-suite RED remains. Next: tests first, original RED, then minimal atomic implementation, candidate GREEN, independent review and checkpoint.
