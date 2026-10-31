# Run35 closed real-file checkpoint — matched-parameter slot-locality ablation

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run34 #1361. Prereg blob `41745d62182e4cf79e8e7a729d3fb360546490d2` committed first at `952c40740016dce7f77382d0db45aa1b6ec758c3` before any seed301 fit. Frozen original Z12b and Run28 slot model/collectors unchanged.

## Original real-file evidence verified

Actions **41148459105** at exact source HEAD `c60383bc0a02311a9f8033334bfde64a96e5de2b` completed SUCCESS. Original artifact **13022096998**, ZIP SHA256 `4e9870c1f6530990ebd987d34b6efd324f1b93f9e8b9d974a29f74c5e294160b`, CRC PASS, **75/75** inner SHA256SUMS exact, PINS/VENV/DEPS/TEST/REALFILE/REPORT_CHECK/COMPILE/PRIVACY/DIFF all exit 0, 18/18 tests PASS, privacy CLEAN. Six per-seed checkpoints `work/{aligned,scrambled}-{301,302,303}-RESULT.json` independently compared to aggregate after removing diagnostic-only `_conf_err`: exact identities PASS. Private permitted Library backup `/V13-Checkpoints/2026-10-31/Run35-WorldJepa-SlotAlignment/run35-realfile-41148459105-sha4e9870c1.zip` independently materialized byte-identical.

New seeds301–303, **the same collected real-file rows** per aligned/scrambled pair, train4000/cf150/attr300/steps3000, same Run28 trainable model parameters, same 96D concatenated latent, fixed bijective wrong-locality feature permutation, original action IDs unchanged. This isolates slot alignment, **not** the remaining global-96D model-capacity confound.

Aligned mean covered counterfactual retrieval **0.9413**, scrambled **0.2746**, mean difference **+0.6667**; per-seed differences **+0.6810, +0.6585, +0.6606**. Aligned vs scrambled both-world action attribution gain difference **+0.227967**. Both prereg exploratory locality diagnostics **L1 PASS, L2 PASS**. This supports correct slot/action alignment as an important contributor on this synthetic file-world task, not general JEPA utility.

Original binding gates remain negative: aligned **W1/W2/W3/W5 PASS, W4 FAIL (Spearman −0.2789 vs <=−0.30), W6 FAIL**. Scrambled **W1/W2/W4/W6 FAIL**, W3/W5 PASS. Aligned W7a PASS, **W7b FAIL** (mean none-self gain **+0.0498** below +0.05), **W7c FAIL** (mean four-class macro +0.095508 but seed303 +0.0331 below +0.04). Scrambled W7a/b/c FAIL. Overall **SHADOW_CANDIDATE_FAIL**, no threshold adjustment, no cherry-picked seed exclusion. Original W6 balanced no-action baseline remains near ceiling: aligned JEPA 0.9522 vs no-action 0.9534.

## Next step

The complete 96D-global versus slot-shared matched-capacity comparison remains unproven; W4 confidence and W6 no-action attribution ceiling require new preregistered interventions, not retroactive changes. Run36 disjoint AG12 native confidence-incidence collector is independently software GREEN and may now launch because Run35 heavy is terminal. Exact reproducibility command for this cohort (new fresh paths, original pins): `cd v13/code && PYTHONPATH=.:tests:scripts python scripts/run35_world_jepa_slot_alignment_real.py --out /fresh/RESULT.json --work-root /fresh/work`. **Do not rerun as a replacement** for this original measured cohort; retain failed gates and original ZIP.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no Redmi, no learned German transfer, no live JEF or whole V13 completion. No production merge/auto-merge.
