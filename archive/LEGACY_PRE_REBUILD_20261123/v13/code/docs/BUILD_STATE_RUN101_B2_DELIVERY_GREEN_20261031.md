# Run101 real Context OS B2 wide-vs-narrow delivery GREEN — 2026-10-31

Owner GPT-6 Auto11, review-only child of Run100 #1466 exact parent `b9282da0b532aa1a87daf73f86b64eaf5697a898`; prereg `ac551b1264c14a02a56150be7d981fcdac3f0c42` before tests. **No frozen runtime changes, no native model calls, no original Run87 rescore.**

## Verified actual software behavior
New `tests/test_b2_wide_narrow_actual_consumer_20261031.py` uses **real Runtime, Store, Cognition, persisted QueryPacket/OfferPacket, actual `Cognition.analyst_context`** with an explicit synthetic fake B2 generator selecting the same exact archived budget sentence by quote-choice ID. Two turns share an explicit project; no C3/native inference or assistant output.

With `offer_quote_context_chars=400`, the verified prior quote pointer expands to the **full exact earlier source** (budget, deadline, local-only rule), `EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE`, `semantic_truth_authority=false`. With width 0, the same selected pointer yields **only** the exact budget sentence, `EXACT_SOURCE_SUBSTRING_ONLY`, no other prior rule. Deleting the earlier source causes fail-closed consumer rejection; wrong event and mutated OfferPacket are rejected. Thus the Run87 widened source-ref/short-quote mismatch is consistent with an **intentional functioning Context OS source transport**, not absence of prior rule data. This is software/synthetic consumer evidence, not proof a real C3 uses the rules or computes the correct option.

## Original CI and persistence
Actions **41205321929**, exact tested HEAD `bf8b2165566fae5a594bf28887bdb9e2e67f437e`, terminal GREEN. **4/4** real-store/fake-generator consumer tests, **9/9** Run100 strict subspan candidate tests, **12/12** frozen Run87 fixture tests, **16/16** original synthetic native verifier tests (**41/41** total); VENV/DEPS/COMPILE/DELIVERY/CANDIDATE/FROZEN_FIXTURE/FROZEN_VERIFY/PRIVACY/DIFF exit0, privacy CLEAN. Original artifact **13043933787**, ZIP SHA256 `a079afeaf9df80f38a42f6d74dbb5a4749eefbeb013161d6a08cddd87b35b68c`, 4595 bytes, CRC PASS, **20/20** SHA256SUMS PASS. Private original ZIP `/V13-Checkpoints/2026-10-31/Run101-B2-Wide-Narrow-Delivery/RUN101_ORIGINAL_DELIVERY_41205321929_SHAA079AFEA.zip` re-materialized byte-identical.

## Next step
Do **not** replace the widened refs with narrow candidate automatically: the verified wide path carries all three earlier rules from one quote pointer, whereas narrow loses two. Next canonical package should test the real **C3 answer consumer** with an explicitly labeled synthetic receiver first, then preregister a **new disjoint native** B1/B2→C3 decision cohort whose extraction and decision scores match the questions actually asked. Original seed877 scores, prior RED, native models, source hashes, and negative gates stay immutable.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. No production merge.
