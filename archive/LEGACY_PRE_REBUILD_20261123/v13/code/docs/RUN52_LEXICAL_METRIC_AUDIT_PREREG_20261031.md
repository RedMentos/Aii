# Run52 B1 lexical metric adversarial audit prereg — 2026-10-31

Owner GPT-6, independent read-only audit child of Run52 software-preflight head `2211863105802d3192bd6247546dab3ce7deb761`. Run52 owner, seed479 fixture SHA256 `5cc8783dedbb201a0a8b86763c99dc23130e1d126a603cf0afcac33d8b985f3b`, original scorer, model/source pins and future native rows remain **frozen and untouched**. This is a **post-registration diagnostic of metric specificity**, never a posthoc rescore or gate change.

## Precommitted hypothesis

Run52 `b1_signal` and independent `lexical_b1` match `\\b(?:option\\s*)?A\\b` case-insensitively. This can match the ordinary English article `a` in a summary that explicitly selects **Option B**, as long as the expected remaining integer appears anywhere. The numeric check `(?<!\\d)30(?!\\d)` may also accept a decimal `30.5` or negative `-30`. NONE regex can match an incidental `none` while a positive option is named. These are false-positive risks in the *narrow lexical B1 signal*, not proof of incorrect native model behavior.

Implement a deterministic synthetic counterexample corpus and an isolated conservative future-metric candidate. Independently show original runner and replay scorer agree on the same false positives, then show candidate rejects them while accepting two explicit unambiguous positive phrasings. Do **not** edit original `run52_b1b2_cross_turn_native.py`, `run52_b1b2_cross_turn_verify.py`, fixture, prereg or any raw native evidence. Do not use candidate to relabel seed479 or claim Run52 failed; document that a fresh preregistered disjoint native cohort is required for a replacement metric. CI focused software test + original Run52 tests + frozen pins + privacy/diff + raw artifact.

Negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, Redmi UNMEASURED, whole V13 incomplete. No production merge/auto-merge.
