# B3 L1 attempt 7 (WP-Z4e) PREREG: power — same recipe, five times the data, one fresh seed

Written 2026-10-27 before any state of data seed 20261301 is computed. Script `scripts/b3_l1_v7_bench.py`.

## Why
Attempt 6 (WP-Z4d): LATENT was ahead of the attribute-word baseline on private/escalate on all three fresh seeds
(+.056, +.015, +.040) and on private/apologize on all three (+.003, +.036, +.003), but with 120 test rows per split the
canon rule (paired mean − 2 se over 5 split seeds, against label word AND attribute words) passed only sometimes. The
attempt-6 summary named power as the limit and ruled out further readout tweaks on the 600-row design.

## What changes (only this)
- N = 3000 rows on one new data seed 20261301 (0 sender texts shared with attempts 3-6, checked before the run), so
  600 test rows per split. New B1 LFM2.5-1.2B / B2 Qwen3.5-0.8B states (same files and hashes as attempts 4-6).
- Private view, tasks escalate and apologize only. Action (seed-dependent 2:2) and the shared view are not rerun.
- Recipe, baselines, splits, 5 split seeds, `BB.l1_gate`, canon rule, bridge save on PASS: unchanged (`b3_l1_v5_bench.run_task`).

## Expected power (stated before the run)
Mean prior LATENT − attribute-word gap: escalate ≈ +.037, apologize ≈ +.014. With 5× the test rows the split se should
shrink by about √5 (from ≈ .02-.03 to ≈ .01). Rough chance to clear mean − 2 se: escalate ≈ 70-80 %, apologize ≈ 20-30 %.
A FAIL here at this power counts as evidence against a useful L1 gain on that task, not as "not enough data".

## Verdict
Per task: canon PASS/FAIL exactly as in attempts 4-6. G-CALLOSUM-UTILITY-002 needs more than L1; a PASS here only re-opens the
L2 prefix SHADOW experiment for that task (as after attempt 4). A PASS on escalate is still one seed: it must be replicated on a
second fresh 3000-row seed (20261302) before any L2 work. LATENT authority stays 0; runtime unchanged.

## Amendment A1 (2026-10-27, after the first start crashed before any result)
The first start died while computing states: the Linux OOM killer ended llama-server (8.7 GB) at the third embedding stage,
before any model output was evaluated (no accuracy was seen). Change: state computation only — stage files on disk, a fresh
server per 500 texts, fp16 tokens in chunks. Texts, models, data, recipe and criteria are untouched.

## Amendment A2 (2026-10-27, after seed 20261301 finished: canon PASS on both tasks)
Seed 20261301 result: private/escalate and private/apologize both canon PASS (see `BEFUND.md`). As stated above, the replication
on a second fresh 3000-row seed (20261302, 0 shared sender texts with all earlier seeds, checked) is run before any L2 work. The
script accepts the data seed only from the preregistered pair via `B3V7_SEED`. Replication rule: canon PASS on the same task
on seed 20261302 = replicated; otherwise NOT_REPLICATED and L2 stays locked. Nothing else changes.
