# Run11 half-parser review addendum: spaced/unicode sign falsifiers — 2026-10-28

Independent follow-on inspection after initial review patch, before this second patch. The parent contract forbids signed operands. The first counterexample guard rejects *additional* digits outside the selected integer, but a single number with a separated sign can still be matched as unsigned (e.g. `Halbiere - 120`), as can Unicode minus `−120` and word-sign `minus 120`. These are newly registered counterexamples, not retroactive edits to the original frozen cohort.

Negative controls: `Halbiere - 120`, `Halbiere + 120`, `Halbiere −120`, `Halbiere – 120`, `Halbiere minus 120`, `Calculate half of negative 80`. Positive controls remain `Halbiere 8.` and `Budget 120 Euro. Berechne die Hälfte.`.

Narrow change: reject a unary sign token immediately before the sole matched integer, including whitespace-separated and word-sign forms. Do not modify generic expression handling, tool permissions, Age0 shadow policy, or any model/runtime. Software tests and new exact-source CI run required. The initial CI result, whether PASS or RED, remains scoped to its original source SHA.
