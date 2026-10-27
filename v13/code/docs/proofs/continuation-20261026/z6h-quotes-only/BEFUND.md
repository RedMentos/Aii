# WP-Z6h BEFUND: body quotes only (hypothesis text removed)

Verdict: **Z6H_QUOTES_FAIL** (prereg `PREREG.md`, committed 9bac99d before the run; seed 47, 60 tasks). The run was
interrupted by a container restart after the `disabled` arm; the three other arms were resumed unchanged on the same
seed (the script keeps finished arms). Data: `v13/bench-results/z6h-quotes-only-20261026/z6h.json`.

| arm | passed /60 | breaks vs C3 alone | rescues | mean time |
|---|---|---|---|---|
| disabled (C3 alone) | **38** | - | - | 2.3 s |
| max+hide (no hypotheses for C3) | 35 | 4 | 1 | 15.6 s |
| max+quotes (only verified quotes) | 34 | 12 | 8 | 15.2 s |
| adaptive+quotes | 27 | 13 | 2 | 7.6 s |

- H1 max+quotes 34 < max+hide 35 + 2. FAIL. H2 12 breaks > 4. FAIL. H3 34 < 38. FAIL.

## What it shows
- Verified quotes alone do not help C3 either: they swap 8 rescues for 12 breaks (net -4). Any extra block in C3's
  prompt moves its answers; on these tasks that costs more than it brings.
- Three measurements in a row (Z6e, Z6g, Z6h; seeds 37, 43, 47) put C3 alone at or above every body arm. adaptive is
  always the worst arm (28, 32, 27).
- max+hide is 3 below C3 alone here (4 breaks, 1 rescue) — the run-to-run noise level of this bench (Z6g: 4/4).

## Next
Do not hand body output to C3 for answering at all by default; use bodies after the answer (observers, late correction,
Inquisition) where they cannot overwrite it. This is the open default decision put to the user. Claim limit: bench
hook, generated English tasks, regex checks, one seed, cloud.
