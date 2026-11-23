# Run12H — independent Age0d arithmetic assertion-scope review (2026-10-30)

Owner: GPT-6. Review-only child of PR #1263, draft PR #1264. Canon and frozen `selfmodel.py` unchanged; no Runtime consumer, delivery, learning, age or gate authority. This is a **synthetic source-only review**, not real model-answer calibration.

## Reproduced false alarm and narrow change

At original Run12F blob `899b8e32d94725adec9beb134be2620b72fc1d5d`, `inspect("Review the statement", "It is not true that 2 + 2 = 5.")` returned `POSSIBLE_ARITHMETIC_ERROR_SHADOW`. This incorrectly treats a negated false premise as the assistant's own numerical assertion.

Candidate blob `74383c570df068de7d647184d8c6e85ae3e1e125` conservatively returns `ABSTAIN/NON_ASSERTIVE_EQUATION_CONTEXT` for negated, hypothetical, question-mark and other clearly nonassertive contexts. This intentionally loses some coverage to avoid false alarms; it is not a full semantic assertion-scope parser. New test blob `30b2817e9ac0ca2f5c3303c8be552cf5b79f862c` covers 16 nonassertion cases and preserves detection of plain asserted wrong equations, correct equations, and strict bare-integer question/answer pairs.

## Exact original evidence

- Actions: https://github.com/RedMentos/Aii/actions/runs/41049787198 — **SUCCESS**, source-only, tested HEAD `96bc5d5c808d5a41bd58a0a48e90d88a1902942d`.
- **16/16** unittest methods PASS (12 original + 4 new); 16 nonassertion cases are subtests. Independent old-vs-new reproduction PASS. PINS/TEST/COMPILE/REVIEW/PRIVACY/DIFF all EXIT0; privacy **CLEAN**.
- Original artifact ID **12973588922**, original ZIP SHA256 `8815dee61e54719a52a27a9edcdd946d645b4b9dae8336f670de1a9bcb279e7a`, 11,133 bytes, CRC PASS, **17/17** manifest hashes verified.
- Private Library backup `/V13-Checkpoints/2026-10-30/Run12H-Age0D-AssertionScope/V13_Run12H_Age0d_41049787198.zip` re-materialized and independently byte-compared: **EXACT**.
- Source pins: candidate `74383c57`, tests `30b2817e`, existing Run12F tests `444e8e39`, frozen selfmodel `072ae59d`, immutable Canon `218464b1`. All Git blob hashes matched in original raw.

## Explicit negative gates and next command

Age0 **RECORD_ONLY**; late-correction delivery **NOT AUTHORIZED**; STEP2 **UTILITY_FAIL**; B3 **NO_PROMOTION**; Body-JEPA **UNAVAILABLE**; `jepa_weight=0`; Redmi **UNMEASURED**; V13 **INCOMPLETE**. No model or native experiment was performed. Run12F original GREEN and historical REDs remain intact.

Next: use a disjoint, predeclared set of real model final answers and adversarial nonassertions to estimate false-alarm and missed-error rates before considering Age0d integration. This review is not a promotion recommendation. Continue independent Canon organs while the other owner's Run12G calibration branch remains separate; do not overwrite that branch.
