# Run223 preregistration — DS3 held-out distribution-shift guard (LAB ONLY)

Base Run222 verified head `d0bf78b933718b4def9bb821c1683af7c5d5b498`. Owner: sequential narrow change to `v13/agi/ds3_selective.py` **evaluate() report only**, new test/bench/CI/proof. No Runtime, model, JEF, tool, age or approval changes.

Research: Geifman & El-Yaniv, NeurIPS 2017 selective classification https://papers.neurips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html ; Angelopoulos et al., ICLR 2024 conformal risk control https://arxiv.org/abs/2208.02814. Run222 uses a fixed-grid Hoeffding/union bound **only under i.i.d. calibration assumptions**. Distribution shift breaks the assumption. This run explicitly probes that limitation, not a new guarantee.

Locked shift holdout (never used to recalibrate): 300 high-confidence test examples at score 0.95, **270 wrong**; 200 low-confidence test examples at score 0.55, **20 wrong**. Calibration stays exactly Run222's fixed 600 high/400 low cohort, no threshold retuning. Expected selected coverage 300/500 = 0.60 and selected error 270/300 = 0.90.

H1: `evaluate` reports the actual shifted risk 0.90, `holdout_target_pass=False`, `distribution_shift_warning=True` when risk exceeds 0.10; no misleading calibration guarantee.
H2: original independent Run222 holdout retains risk 5/300 and `holdout_target_pass=True`, but **deployment_allowed=False** even on synthetic PASS.
H3: no external tool execution, model weights, live C3, Age or gate promotion. The original negative gates remain unchanged.

The test must fail RED against Run222 before the narrow report-only change, then pass GREEN. Preserve raw logs, no threshold tuning on the shifted holdout. A genuine native C3 confidence experiment needs a new preregistration and source/model hashes.
