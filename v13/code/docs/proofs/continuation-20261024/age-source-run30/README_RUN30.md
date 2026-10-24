# V13 Run30 — Age independent-source noise signal (SHADOW) — FAILED cohort

Base PR65 `f6938f4b9f8cbd42a117d725264f5cc9bd4f1abb`, owner Codex Run30 isolated. This is a new WP-Z8 candidate addressing the documented G-AGE-REOPEN-001 failure: Age's own error cannot distinguish noisy labels from genuine shift. It uses only repeated comparable case labels from purportedly independent external sources; no own model error, no model truth authority, no AgeControl writes. Source identities/quality remain unverified input assertions. Binary labels only; does not yet handle continuous Z8 stream.

Pre-registered thresholds (see PREREG_RUN30.md SHA256 5083cd...) before cohort: two distinct agreeing sources per case in each window, at least three cases changed and >=80% changed; 100 seeds with four independent sources and 10% random flips, PASS only if >=90/100 shifts detected and <=5/100 false shift.

**Result: FAIL** — 40/100 shifts detected, 0/100 false shift. Strict unanimous agreement discards too many useful cases. 8/8 software tests PASS. The failed original cohort and thresholds are retained. No post-hoc promotion or threshold change. This result does not alter the earlier Z8 K1–K7 FAIL.

Next: pre-register a separate v2 majority-vote candidate with source diversity and noise bounds; run fresh seeds, compare against this failed v1. Do not turn on Age plasticity from this signal until independent provenance and actual AgeControl outcome test pass.

All other V13 gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; full system INCOMPLETE. No native LLM or Redmi test, no full repository checkout/privacy scan.
