# B3 L2 prefix SHADOW, private/action only (WP-Z4b, cloud, 2026-10-21)

Next step after the canon L1 PASS of attempt 4 (`bench-results/b3-l1-v4-20261021/`, B3-H8 step 7). Script `code/scripts/b3_l2_prefix_bench.py`, native runner `code/scripts/native/b3_prefix_embd.cpp`, gate `v13/b3bridge.l2_gate`, preregistration `code/docs/proofs/b3-l2-prefix-20261021/preregistration.json` (pushed before any real-label measurement).

What was tested: the attempt-4 aux bridge message (4 slots x 8, 64 B BF16) is aligned into the native input-embedding space of the frozen receiver (Qwen3.5-0.8B Q4_0), calibrated to its native token statistics and fed as **4 continuous prefix slots through the receiver's own input path** (llama.cpp b10964 `batch.embd`, IMROPE positions). The readout is the L1 NO_MESSAGE readout on the receiver's pooled states over its **own** private-view tokens; prefix positions are excluded, so every gain has to pass through the frozen backbone. Text baselines (EXACT cue span, SYMBOLIC label word, SYMBOLIC_ATTR level words) enter as their own token embeddings at the same position with the same readout.

Checks before and during the run: runner without prefix = attempt-4 pooled receiver states (max rel. L2 1.3e-7); the attempt-4 L1 result was reproduced exactly (per seed identical, seed-0 bridge digest = artifact `3c75aad1…`); 8-item rerun bit-identical.

## Result (5 seeds, test 120 items each)

| channel (receiver backbone read) | acc | utility |
|---|---|---|
| PREFIX_OFF (= NO_MESSAGE) | 41.5 | 0 |
| **PREFIX, PCA_ALIGN (primary)** | **80.2** | **0.383** |
| PREFIX, EXACT_ALIGN (exploratory) | 77.5 | 0.356 |
| PREFIX_SHUFFLED / PREFIX_RANDOM (PCA_ALIGN) | 37.5 / 37.8 | <0 |
| EXACT (430 B cue span as tokens) | 76.5 | 0.323 |
| SYMBOLIC (label word as tokens) | 81.5 | 0.400 |
| SYMBOLIC_ATTR (level words as tokens) | 74.8 | 0.332 |
| reference: L1 adapter read (attempt 4) | 90.0 | — |

- **Preregistered verdict: L2 FAIL on private/action** (primary PCA_ALIGN). Passed: beats prefix off (+38.7 points, 5/5 seeds), shuffled and random controls (both at or below chance, so the content of the prefix matters, not its presence), utility beats EXACT (+0.060) and SYMBOLIC_ATTR (+0.051), role retention (retrained topic head drop 0.002), calibration (norm ratio 0.998, mean shift 0), bit-identical rerun. **Failed: utility vs the SYMBOLIC label word (−0.017, the sender's own one-word answer is as good or slightly better).**
- EXACT_ALIGN (exploratory): also FAIL (not significant against EXACT, SYMBOLIC and SYMBOLIC_ATTR).
- So the receiver backbone **does** take up the calibrated latent prefix and carries the task information into its own token states, but on `action` (sender-computable task, three classes) a single label word does the same job for 8 bytes. That is the honest symbolic case the attempt-3 design already named.

## Additional findings (reported, not gated)

- L2 is clearly **below L1**: 80.2 vs 90.0 (−9.8 points, 0/5 seeds better; the `paired` helper only tests "better", so its `significant: false` here means "not better", the drop itself is about 8 standard errors). Passing through the frozen backbone loses information compared with reading the message directly.
- Full 1024-dim readout (exploratory): PREFIX 84.7, EXACT 80.2, SYMBOLIC 81.5.
- **Old-readout drift:** a topic head trained on prefix-off states drops from 100 % to 40 % on prefixed states (pooled-state cosine 0.94). With a retrained head the drop is 0. Any L3 or later step needs receiver readouts recalibrated per prefix or must leave existing heads untouched.
- Calibration packet (PCA_ALIGN, seed 0): native token norm 0.659 ± 0.076, prefix norm 0.658, variance ratio 1.10, top-8 native PCs hold 44 % of the native variance, scale 1.59. EXACT_ALIGN: ridge reconstructs the cue-sentence embeddings poorly (select R² 0.15).

## Consequence

B3_LATENT stays at **L1_shadow** for private/action; L3 (tiny residual) stays locked; LATENT authority 0; runtime unchanged, no bridge installed. A new L2 attempt only makes sense on a task without a cheap sender-side label word (escalate/apologize need receiver-private information, but they failed L1), or with a stronger L1 bridge for those tasks first.

## Evidence and limits

`report.json` (per-seed numbers, gate criteria, calibration packets, hashes), `run.log`. Inputs: attempt-4 `states.npz` (project folder only), receiver GGUF sha `57d19977…`, runner linked against the b10964 release `libllama.so`. Runtime 41 min, Linux x86_64 cloud CPU (4 threads), not Redmi. Claim limits: one synthetic task with the same templates that were used to design the aux fix; frozen bodies; prefix only before the private text; SYMBOLIC text uses a fixed wrapper sentence ("Suggested action: <word>.") whose bytes are not charged, as in L1.
