# Run39 prereg — action-balanced all-six-slot World-JEPA SHADOW (software first)

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run38 PR #1365 at exact `804918aaac79676f3872bf8dba0edbe1d3accc35`. **Commit this prereg before candidate code, new file-world collection or fit.** Original Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` and all Run29/32/35/38 cohorts, thresholds and failed attempts remain frozen.

## Motivation and intervention

Original Run28 two-slot shared-core training samples one affected operation slot and one unaffected noop slot per non-noop transition (~1:1 local action/noop rows). Run38 all-six-slot training samples one affected slot plus five unaffected noop slots (~1:5); it covers every physical slot but dilutes the action-bearing examples to ~16.7% for ordinary affected transitions. Run38 heavy disjoint seeds401–403 **still running and unverified** at prereg; this proposal is not a posthoc adjustment to Run38 results.

New isolated `BalancedFullSlotWorldJEPA`: for every original transition, include all six physical slots exactly once; if the action affects a physical slot, add **four extra copies of that affected slot/action/next-state triple**, yielding five action rows and five noop rows. For global noop and zero-action controls add no duplicates; all six noop or six zero vectors remain intact. Use the same frozen `WorldJEPA` shared 10D-observation/6D-action core, EMA, inverse head, 16D local latent, 96D concatenation, optimizer, steps and full action support. This intervention changes row multiplicity, class balance, effective example count and sampling distribution, **not** model parameters. Duplicates are not independent observations. This is not a compute-matched or global-96D capacity control.

## New registered cohort and original binding gates

**Future** disjoint seeds **501,502,503**, train4000/cf150/attr300/steps3000. One fresh file-world collection per seed, exact in-memory rows shared across three arms: frozen original Run28 two-slot, Run38 unweighted six-slot, and new action-balanced six-slot. Each arm trains true-action, zero-action and shuffled-action controls with the original Run35 evaluator; no raw private user data. Same original Z12b W1–W6 and Run35 W7a/b/c thresholds; no retuning, exclusions, source/model swaps or posthoc gate waiver.

Exploratory **H1**: mean balanced action-minus-no-action attribution gap of action-balanced six-slot exceeds unweighted six-slot by >= .05, with no seed worse than -.01. **H2**: action-balanced six-slot covered CF retrieval >= .80 each seed and original W2 controls fail. **H3**: its W7c four-class macro action gain exceeds unweighted six-slot by >= .03 mean, with no seed worse than -.01. These are descriptive subgates; candidate remains SHADOW and cannot pass unless **all original W1–W6 and W7** also pass, with separate utility/approval/Redmi gates still required.

Software preflight must prove exact 6+4 row mapping for affected actions, global noop and zero controls, original input immutability, full-action support, exception atomicity and frozen original model source. All new source and tests pinned before heavy. **Do not launch native heavy while Run38 Actions 41151531032 or another owner is active.** Reuse serial group `v13-native-c3-ag12-20261030`; retain all failed raw/per-seed checkpoints and original hashes.

Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no Redmi, learned German transfer, JEF fusion or whole-system completion.
