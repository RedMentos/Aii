# WP-Z6i PREREG: §24.17 Deliberation trajectory / halting (real C3/B1/B2)

Written and committed before any run. Script: `scripts/z6i_halting_bench.py`.

## Question
Blueprint §24.17 asks for: a fixed-depth baseline, a post-hoc/simple halt readout, a trained halt head, a quality-vs-latency
Pareto view, no disproportionate loss on hard examples through early exit, and that trained halting is only adopted if it beats
the frozen/post-hoc baseline. §24.17 was only TESTED (existence tests), never measured with real models.

## Setup
- Depth = number of targeted body re-entries after the first B1/B2 offers in the focal loop (WP-T1). Effort `max` (both bodies).
- Real arms per fixture (fresh home per arm, temperature 0, post-commit observers cut, same handling as Z6a/Z6e):
  `c3` (C_native only, reference), `scaf` (shipped scaffold; Age 0 caps the focal loop at one cycle), `d0`/`d1`/`d2`
  (forced depth 0/1/2; bench-only patch; d2 lifts the Age-0 one-cycle cap — claim limit).
- Halting policies decide once after the first B1/B2 offers: halt = d0 outcome, continue = d1 outcome (read from the
  deterministic runs; validity requires identical first offers in d0 and d1 on >= 90 % of fixtures, else `Z6I_INVALID_PREFIX`).
  - `posthoc`: continue iff the two first offers disagree (`focal.disagreement >= BOOT disagreement_trigger` = .40).
  - `trained`: the real halt-head path (`readout_worker.train`, frozen C2 Needle embeddings of input + .2 × B1/B2
    trajectory as in `learning.readout_embedding`), labels from training seeds: continue iff d1 passes and d0 fails;
    scaffold label = posthoc; out of support / uncertain → posthoc. If the trainer refuses (fewer than six labels per
    class), `trained` is reported `NOT_TRAINABLE` and K5 fails.
- Fixtures: `z6e_wake_bench.fixtures` (12 each of easy, exact, long, mixed, conflict = 60). Training seeds **83, 89** (arms
  d0, d1); test seed **97** (all five arms). Seeds not used by earlier Z6 benches.
- Hard examples = test fixtures that `c3` fails.

## Criteria (per halting policy; test seed 97)
- K1 not dominated: no fixed depth d0/d1/d2 has significantly more passes (sign test p < .05) at no higher mean time.
- K2 hard examples: losses against the deepest fixed arm (d2) on hard fixtures, as a share, are at most the share on the
  other fixtures + .10.
- K3 quality: passes >= best fixed depth − 2.
- K4 cost: mean time to answer below the deepest fixed arm.
- Policy PASS = K1–K4. Verdict `Z6I_HALTING_PASS` if at least one policy passes, else `Z6I_HALTING_FAIL`.
- K5 (adoption of trained halting): trained passes K1–K4 **and** beats posthoc (more passes, p < .05; or no fewer passes and
  < 90 % of its mean time). Otherwise `KEEP_POSTHOC`.
- Reported, not gating: Pareto front over all arms and policies (incl. `c3`), paired d1 vs d0, d2 vs d1, c3 vs d0/posthoc,
  scaf vs d0/d1, rescue/break lists, continue rates.

## Honesty rules
No default changes from this bench. If `c3` alone is on top again (Z6e/g/h), it is stated as the main finding.
Claim limit: generated English tasks, regex checks, deterministic bench decoding, cloud CPU, no energy, one test seed.
