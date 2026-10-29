# HB0d — posthoc explicit-recommendation coverage audit (2026-10-29)

Owner: GPT-6 automation, isolated review child of PR #1050 exact `17c989f1cf2f7f5ca25d388afa47044d6f69898b`. This note is committed before audit implementation. **POSTHOC EXPLORATORY ONLY**: it does not modify or supersede the HB0c preregistered prefix parser, native RAW, SCORE, original cohort, or acceptance gates.

## Source and question

The independently verified Linux-native HB0c run `40829097897`, artifact `12877896675`, exact HEAD `17c989f1cf2f7f5ca25d388afa47044d6f69898b`, produced 24 native responses. Original RAW.json SHA256 `dbaf4fd299138c21c5a6f2de4bd52f092abc73f1f165c4ae447c962799e7b638`; original SCORE.json SHA256 `8dc551c43c5223581b2eaf8116107f8e6aea8679586817aa4a22993d5056b971`. The original strict initial-prefix parser marked all 24 unparseable. The new audit asks only whether some responses contain an **explicit unambiguous recommendation outside the original prefix**, and whether the measured difference is parser coverage rather than model utility.

## Rules fixed before posthoc analysis

- Read the original closed evidence from the original exact-head GitHub Actions artifact. Require external SHA256 pins for original RAW and SCORE and independently verify the artifact SHA256SUMS, HEAD, receipt, model/runner identities, raw input hashes, 24 unique ordered row-arm keys, and the unchanged original SCORE computed from the original parser. Never alter original evidence or source/model/seed/cohort hashes.
- Candidate extraction is deliberately conservative: identify explicit choice/recommendation/selection phrases (Option A/B), explicit no-eligible-option commitments (NONE), and explicit inability to decide (UNKNOWN). Mere mentions of Option A/B in descriptions, costs, questions, hypothetical, negated advice or copied task text are not commitments. If multiple conflicting explicit commitments occur, return AMBIGUOUS; otherwise if none, return UNPARSEABLE. Output decision evidence only as a category and character offsets, never raw model text in the public report.
- Audit the six paired public synthetic tasks × four native arms; output per-arm count of explicit extracted decisions, ambiguous, unparseable, unknown, exact and wrong-committed versus the original separately joined oracle. Include row-level IDs only as SHA256 digests, never raw outputs. Keep original strict parser counts unchanged in separate fields. All counts must sum to six per arm and 24 total.
- Synthetic unit tests must include true positives and adversarial negatives: mere option mentions, negation, quoting, hypothetical, multiple contradictory recommendations, no-option statements, uncertainty and tampered/missing original evidence. The raw-run evaluation remains posthoc; no parser tuning based on the 24 raw answers after first audit.
- Source-only CI and a separate pinned evidence audit workflow may be used; do not rerun native model inference, alter active owner, or publish private data. Keep raw native artifacts at the existing private destination only; the GitHub artifact has its existing retention. A failed retrieval or mismatch produces RED with no result promotion.

## Interpretation

Any extracted exact count is exploratory, neither a preregistered success nor evidence of B1/B2 native offers, learned complementarity, foreign-source rejection, blind holdout, Redmi performance or whole-system utility. No STEP2/B3/Body-JEPA/LP3/jepa_weight/age promotion: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE.

Next substantive work remains the separately registered fresh 150-row model/source-native experiment with real B1/B2 offers, one-body controls, shuffled foreign sources and a C3-alone baseline.