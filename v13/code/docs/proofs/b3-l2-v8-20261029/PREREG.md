# WP-Z4f PREREG: B3 L2 prefix SHADOW on private/escalate and private/apologize (written before any real-label L2 number)

Why now: B3 L1 attempt 7 gave canon PASS on both tasks on two fresh 3000-row seeds (REPLICATED, commit aea13abe). B3-H8 then allows the
L2 prefix SHADOW test. The user gave the go-ahead on 2026-10-29.

## What is tested
Identical to WP-Z4b (`scripts/b3_l2_prefix_bench.py`, native runner `scripts/native/b3_prefix_embd.cpp`, gate `b3bridge.l2_gate`), except:
data seed 20261301, N = 3000 (600 test rows per split), staged attempt-7 states, attempt-7 bridge recipe retrained per seed (recv_cond aux
bridge + refit_readout, 5 seeds, 60/20/20), tasks escalate and apologize, SYMBOLIC text 'Suggested answer: <yes|no>.' (fixed wrapper, bytes
not charged, as in WP-Z4b), only the PCA_ALIGN variant (the exploratory EXACT_ALIGN never passed and is dropped).
Message z[4,8] BF16 (64 B) -> PCA_ALIGN + calibration -> 4 prefix slots in the frozen Qwen3.5-0.8B Q4_0 input path -> mean of the receiver's
final states over its OWN private-view tokens -> L1 NO_MESSAGE readout (PCA 48, standardized, softmax head).
Script: `scripts/b3_l2_v8_bench.py`. Controls: PREFIX_OFF, PREFIX_SHUFFLED, PREFIX_RANDOM. Baselines read through the same path: EXACT, SYMBOLIC,
SYMBOLIC_ATTR.

## Pre-run checks (done before this file is committed, no real-label numbers looked at)
- runner without prefix reproduces the attempt-7 pooled receiver states (reported as `runner_check_prefix_off_vs_l1_cache_max_rel_l2`);
- plumbing smoke on SCRAMBLED labels, 1 seed (`B3V8_SMOKE=1`), numbers meaningless.

## Verdict rule (per task, `b3bridge.l2_gate`, unchanged)
PASS iff: PREFIX beats PREFIX_OFF, PREFIX_SHUFFLED, PREFIX_RANDOM (paired mean - 2 se > 0 over 5 seeds); utility (BYTES_W .25) beats EXACT, SYMBOLIC
AND SYMBOLIC_ATTR; retrained topic head drop <= 0.01; norm ratio in [0.8, 1.25]; bit-identical rerun of 8 items. Single run, FAIL stays FAIL,
no setting is changed after seeing numbers; a changed setting is a new, separately registered attempt.

## Consequence
- PASS on a task: L3 tiny-residual SHADOW test may be considered for that task, only after replication on the second fresh seed (20261302)
  and a new prereg. LATENT authority stays 0, runtime unchanged.
- FAIL: B3_LATENT stays at L1_shadow; L3 locked.

## Expectation (stated in advance)
Uncertain. On action (WP-Z4b) the frozen backbone took up the prefix (80.2 vs 41.5 off) but lost 9.8 points against the L1 adapter read and failed
utility vs the label word. For escalate/apologize the label word is a weaker baseline (L1 label word 80.7/83.9 vs attribute words 87.2/92.2) and the
receiver-private fact must be combined with a graded message, so a PASS vs SYMBOLIC_ATTR is possible but not likely (L2 loses information vs L1).
Claim limits: synthetic templates, frozen bodies, Linux CPU cloud, not Redmi, oracle EXACT span.

## Pre-run checks done (2026-10-29)
Smoke on SCRAMBLED labels, escalate seed 0: all channels at chance (PREFIX .53, off .56, symbolic .56), plumbing runs end to end. Runner without
prefix is compared to the attempt-7 cache in the report. No real-label numbers were seen before this commit.
