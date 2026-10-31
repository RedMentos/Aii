# Run100 prereg — B2 prior-quote source-span forensic and isolated candidate (2026-10-31)

Owner GPT-6 Auto11, review-only child of independent Run87 audit #1464 exact parent `fef9f07613109b1cff19a051fff21741f539c62b`. No changes to original Run87 cohort/seed877, frozen runtime, Canon, model hashes, scoring, native results or scientific verdict.

## Observed raw before implementation
Original Run87 Actions 41200115473 artifact 13042004210 SHA256 `ad396ed6a3ea810f3c18f341a7ac54a92cf27c71586f445082ba4e24415736b1` independently audited and privately byte-backed. The registered native `prior_evidence_refs_verified` scorer compares **the entire** prior `evidence_refs` source span (0..source length) to each short sentence in `offer.quotes` (`run87_b1b2_budget_native.py` and `run87_b1b2_budget_verify.py`). In **all six** B2 LONG rows, at least one exact quoted sentence belongs uniquely to the earlier source (Quartz 2, Rowan 1, Sable 1, Tundra 1, Umber 2, Vesper 2); however, every prior evidence ref spans the full source and none equals a selected short quote. Hence the registered `b2_long_prior_evidence=0` does **not** establish absence of quoted prior text; it is a span-granularity mismatch. Separately, only **two quote choices** are allowed while the fixture requires **three independent archived constraints**, so the existing quote output cannot prove full three-rule coverage. Original scientific scores and RED gate remain unchanged.

## Planned scope and falsifiers
- Add isolated, **non-authoritative** candidate `scripts/b2_prior_quote_span_candidate.py` that maps selected exact quote strings to source-ref subspans without changing source hash/id, only when unique in an explicitly supplied permitted source set; reject absent/ambiguous/repeated/out-of-range/mismatched-source-hash quotes, refuse non-exact normalization. No live Runtime wiring.
- Add focused adversarial tests (unique prior, current/prior ambiguity, repeated prior quote, tamper, Unicode offsets, full-source reference unchanged, missing selection, max quote bound). Run Linux software CI with exact source pins, privacy/diff and raw receipts.
- Preserve original Run87 raw ZIP privately; do not upload it to public GitHub. Do not claim a fixed native B2 benefit or new STEP2 result from synthetic tests.
- Next after software GREEN: independently review quote-choice bundling and source-span delivery in a **new disjoint preregistered** native cohort, while retaining all failed historical attempts.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 INCOMPLETE.
