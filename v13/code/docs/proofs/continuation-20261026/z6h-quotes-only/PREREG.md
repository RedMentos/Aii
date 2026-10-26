# WP-Z6h PREREG: do body quotes help C3 when the hypothesis text is removed?

Written 2026-10-26 before the run (fresh seed 47). Z6g showed the hypotheses block itself costs C3 accuracy (A+B with
the block hidden = C3 alone). Here a body's hypothesis summary is removed and only its source-verified quotes (exact
substrings of the user's message) reach C3; offers without a verified quote are dropped. Same bench hook
(`scripts/z6g_offer_number_guard.py`, flag `quotes`), runtime unchanged.

Arms (fresh homes, Z6e/Z6g bench mode, 60 tasks): disabled, max+hide, max+quotes, adaptive+quotes.

## Criteria (all for Z6H_QUOTES_PASS)
- H1 max+quotes passes >= max+hide + 2.
- H2 max+quotes breaks (disabled passes, max+quotes fails) <= 4.
- H3 max+quotes passes >= disabled.
Reported: adaptive+quotes, breaks/rescues, hook counts. FAIL stays FAIL. Claim limit: bench hook, generated English
tasks, regex checks, one seed, cloud.
