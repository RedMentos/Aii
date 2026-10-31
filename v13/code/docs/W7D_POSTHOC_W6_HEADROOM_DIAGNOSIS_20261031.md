# W7D posthoc W6 headroom feasibility diagnosis (2026-10-31)

**Evidence scope:** independent analysis of exact original W7D real-file artifact `13031844870`, SHA256 `cd4983514cb67091225a3c309233a69cd7e159dc51ce43c378b3afc707fc88a0`, registered seeds 701–703, frozen original `scripts/z12b_world_jepa.py` `criteria()` and `attr_eval()`. **Posthoc diagnostic, not a preregistered new trial and not a gate rewrite.** Original status `SHADOW_CANDIDATE_FAIL` remains.

Original W6 is `attribution_no_action_balanced <= attribution_jepa_balanced - 0.20`. The balanced attribution rate is the average of two class rates in [0,1], so **jepa_balanced <= 1**. Therefore, with a fixed observed no-action score `c > 0.80`, W6 cannot pass even if the JEPA arm achieves perfect 1.0.

| Frozen W7D arm | Mean no-action balanced `c` | Mean JEPA balanced | Observed advantage | Absolute maximum possible advantage `1-c` | W6 threshold |
| --- | ---: | ---: | ---: | ---: | ---: |
| Balanced six-slot | 0.950233 | 0.953967 | 0.003733 | 0.049767 | 0.20 |
| Delta-inverse six-slot | 0.955900 | 0.961900 | 0.006000 | 0.044100 | 0.20 |

These numbers are direct means of the three raw `work/<arm>-<seed>-RESULT.json` attribution `balanced` values; no synthetic rescore. Even an idealized JEPA rate of 1.0 misses W6 by at least 0.150233 / 0.155900 for these fixed controls. This **does not prove W6 universally impossible** for a different architecture, cohort or legitimate no-action control; those may change `c`. It does establish that tweaking only the candidate JEPA arm against the current frozen observed no-action scores cannot solve W6, and further repeated tweaks on the same evaluated cohort risk selection bias.

Other original blockers remain: W4 confidence/error rho -0.1243 / -0.1478 vs <=-0.30; W7b none/self per-seed gate FAIL. D1/D2/D3 prospective exploratory changes all FAIL. Thus the delta inverse objective did not materially change the action attribution gap or confidence calibration.

**Consequence:** preserve original negative W6/W4/W7b and original raw. Do not lower the threshold, degrade the no-action control intentionally, cherry-pick seeds, or claim the original cohort passes. A genuinely new action/world-disentanglement design requires a separately preregistered, disjoint cohort, frozen controls and explicit baseline feasibility reporting **before** results; its results cannot retroactively replace W7D/W7S. Meanwhile continue other canonical organs, especially JEF/C3/C5/C6 and Context OS, rather than endlessly retuning this isolated helper.

## Cross-cohort check: original W7S disjoint seeds 601–603

As a **separate posthoc check** (not a new preregistered gate), re-read original W7S Actions artifact `13032013538`, exact ZIP SHA256 `c9bdad3ef348833e9b85961db310f7fa9f5af719eaf0f892809c975d41b8fe41`, original HEAD `676ee271bc5f156f911027c3ae203b649f6e3b6a`. CRC PASS, **79/79** inner hashes PASS, seeds 601/602/603 disjoint from W7D but same synthetic world family. The three unchanged original W7S arms also had observed no-action attribution near ceiling:

| Original W7S arm | Mean no-action balanced `c` | Mean JEPA balanced | Absolute maximum `1-c` | Original W6 |
| --- | ---: | ---: | ---: | --- |
| Two-slot | 0.963867 | 0.965833 | 0.036133 | FAIL |
| Six-slot | 0.964300 | 0.958600 | 0.035700 | FAIL |
| Balanced six-slot | 0.964300 | 0.959733 | 0.035700 | FAIL |

Thus **five tested arms across two disjoint seed cohorts** show the same fixed-control W6 headroom bottleneck. This is evidence of a recurring ceiling **in this particular generator/evaluator family**, not a claim about arbitrary environments or architectures. All original W7S/W7D failures, thresholds, source hashes and registered cohorts remain unchanged.
