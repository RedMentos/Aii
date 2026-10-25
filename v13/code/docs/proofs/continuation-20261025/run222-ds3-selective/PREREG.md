# Run222 preregistration — WP-DS3 selective uncertainty (LAB ONLY)

Base: verified Run221 handoff head `f27c9fb9f0c2699b4daab63b2ff0963af02ed6a7`. Owner: **new** `v13/agi/ds3_selective.py`, new test/bench/CI/proof only. No Runtime/C3/JEF/Body edits; no tool effects; Age-0 and original gates unchanged.

## Research basis (primary)

- Geifman & El-Yaniv, *Selective Classification for Deep Neural Networks*, NeurIPS 2017: https://papers.neurips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html — risk/coverage trade-off via rejection.
- Angelopoulos et al., *Conformal Risk Control*, ICLR 2024: https://arxiv.org/abs/2208.02814 — monotone loss risk calibration; **not** directly claimed for this simplified implementation.

Run222 is **not** conformal prediction. It uses a conservative fixed-grid, one-sided Hoeffding + union bound on an independent calibration sample, under an i.i.d. assumption. Data-dependent score distributions, distribution shift and non-exchangeability are not covered. The C3 confidence signal is **not available/calibrated** in this lab; synthetic labels are not native utility.

## Locked before code/results

Fixed threshold grid: `[0.5, 0.6, 0.7, 0.8, 0.9, 0.95]`, target risk `0.10`, family-wise delta `0.05`, minimum accepted calibration examples `200`. Choose the **lowest** threshold meeting `empirical_error + sqrt(log(grid_size/delta)/(2*n_selected)) <= target_risk`. If none, abstain all. Strict unique sample IDs, finite confidence in [0,1], boolean labels, explicit calibration split. Test set must be disjoint.

Synthetic preregistered benchmark (not native): calibration 600 high-confidence examples at score 0.95 with exactly 10 wrong, plus 400 low-confidence examples at score 0.55 with 320 wrong; test 300 high-confidence examples with exactly 5 wrong, plus 200 low-confidence examples with 150 wrong. IDs are fixed and disjoint. A second uninformative calibration has 1000 score-0.9 examples, 500 wrong.

H1: selected test risk <= 0.10 and coverage >= 0.50 on the preregistered separable synthetic test, with no train/test ID overlap.
H2: uninformative confidence abstains all; no threshold is selected.
H3: invalid/missing confidence, insufficient calibration, duplicate IDs, overlapping evaluation IDs and unapproved external tool proposals fail closed; no external action is ever executed.
H4: lab result never promotes STEP2/B3/Body-JEPA, `jepa_weight`, Age or live tool authority.

Report all failures and raw CI logs. No threshold or seed retuning on these registered examples. A future C3/native benchmark needs new independent data and separate approval.
