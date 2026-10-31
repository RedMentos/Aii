# Run115C original native B1/B2 quote-failure forensic — read-only (2026-10-31)

Independent source: original GitHub Actions `41217444357`, artifact `13048159840`, exact outer SHA256 `f2f105dcd5582eef257cd9d5ee944d5ba0a64c4999c3e1c65451ff89924a1cd7`, ZIP CRC PASS. This note is a **read-only examination** of the existing `NATIVE_CASE/report.json`, not a rerun, new cohort, score adjustment, or proof of quote correctness. Native Run115C remains STRUCTURAL_RED.

The original native experiment recorded 18/18 B1/B2 offers, but only 6/12 intended C3 calls before quote-required gating stopped 3 of 6 projects. The original strict `b1_current_verified` / `b2_prior_verified` flags were:

| Project | B1 current | B2 prior | Strict gate |
|---|---|---|---|
| Lumen | true | true | passed |
| Boreal | **false** | true | RED |
| Coral | true | true | passed |
| Delta | true | **false** | RED |
| Helios | true | true | passed |
| Nimbus | **false** | true | RED |

Observed failure classes:
- Boreal B1 generated a purported quote ending in the non-source token `局部`; Cognition verified **zero** B1 source quotes, correctly refusing quote authority.
- Nimbus B1 generated a longer quote containing `局部` and a short literal `local true`; Cognition verified only the short literal, not the preregistered current option quote. The strict B1 current proof therefore remained false.
- Delta B2 generated current-source quotes but no verified **prior-policy** quote, despite a source-bound current B2 hypothesis; the strict prior proof remained false.
- The three passing projects had both required source spans verified, but their body summaries remained fallible and did not establish independent semantic correctness.

Implication for Run116: **separate exact USER source pointers from B1/B2 model hypotheses**, allow absent/partial verified model quotes without pretending the model quoted correctly, and keep the body evidence and source semantic-truth flags false. Run116's new role-separated bridge does exactly that in SHADOW; the native experiment must still independently prove real B1/B2 offer lifecycle, source/plan integrity, C3 FINAL/reap and no authority. It cannot retroactively repair Run115C or claim STEP2 complementarity.

Potential future disjoint experiment: test whether source-span selection/pointer supervision improves *native* B1/B2 quote accuracy against a registered fresh cohort, with strict literal span and provenance scoring, while keeping Run115C original RED immutable. No model or quote claim should be inferred from this forensic note.

Original Run115C and Run115I/J negative gates remain unchanged: Age0 RECORD_ONLY; STEP2 EVIDENCE_NOT_PASSING; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; `jepa_weight=0`; Redmi UNMEASURED; whole V13 incomplete.
