# WP-Z6g PREREG: offer number guard (why do body offers break correct C3 answers?)

Written 2026-10-26 before the run (fresh seed 43). A 4-task smoke run on dev seed 5 only checked that the hook fires
(8 calls, 2 numbers masked); not evidence.

Z6e: every body arm broke 12-13 tasks that C3 alone solved, mostly exact totals. Hypothesis: a body's summary carries
a wrong number and C3 copies it. Guard (bench hook in Cognition.analyst_context only, runtime unchanged): numbers in a
body summary that do not occur in the user's message become '[?]'. Control max+hide: bodies run, C3 sees no hypotheses
(tells whether the damage comes from the content or from the presence of the hypotheses block).

Arms (fresh homes, Z6e bench mode, Z6e task generator, 60 tasks): disabled, max, max+guard, max+hide, adaptive+guard.

## Criteria (all for Z6G_NUMBER_GUARD_PASS)
- G1 max+guard passes >= disabled - 2.
- G2 max+guard breaks (disabled passes, max+guard fails) <= 4 tasks.
- G3 max+guard passes >= max + 5.
Reported: max+hide, adaptive+guard, breaks/rescues per arm, masked-number counts. FAIL stays FAIL. Claim limit: bench
hook, generated English tasks, regex checks, one seed, cloud.
