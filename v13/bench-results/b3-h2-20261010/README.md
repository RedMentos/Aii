# B3-H2 learned message subspace, L1 retry (cloud, 2026-10-10)

Script `code/scripts/b3_h2_bench.py`, bridge `code/v13/b3bridge.py`. Sender B1 LFM2.5-1.2B per-token final states (2048 dim, ≤41 tokens), receiver B2 Qwen3.5-0.8B. Bridge K=4 selector slots, rank 8, message 64 B (BF16), 29 233 parameters, 58 KB weights (B3-H7: Age-0 class, ok). 600 synthetic items, 5 paired seeds, fit/select/test 60/20/20. Receiver view **shared** = same text, **gist** = item names + domain only.

**Test accuracy (mean of 5 seeds)**

| View / task | NO_MSG | EXACT | SYMBOLIC | CONTROL | L1 mean-pool | **LATENT (learned)** | shuffled |
|---|---|---|---|---|---|---|---|
| shared max_item | 55 % | 100 % | 56 % | 56 % | 57 % | **66.5 %** | 48 % |
| shared sum_ok | 52 % | 100 % | 50 % | 51 % | 52 % | 52 % | 51 % |
| shared tone / certainty | 100 % | 100 % | 100 % | 100 % | 100 % | 100 % | 39 / 51 % |
| gist max_item | 32.5 % | 100 % | 52 % | 34 % | 33 % | **61 %** | 31 % |
| gist sum_ok | 53 % | 100 % | 52 % | 52 % | 55 % | 49 % | 49 % |
| gist tone | 32 % | 100 % | 100 % | 64 % | 99.7 % | **99 %** | 37 % |
| gist certainty | 53 % | 100 % | 100 % | 90.5 % | 100 % | **99 %** | 51 % |

**Result.** The learned selector is a real improvement over the first L1 attempt: on max_item it adds +11.5 (shared) and +29 points (gist) over NO_MESSAGE and +10 / +29 over the mean-pool message, beating shuffled/random controls (all 5 seeds). It carries tone and hedging that the receiver cannot see (gist view, 99 %). Arithmetic (sum_ok) is not carried at all.
All B3-H2 diversity checks pass: role retention drop 0, gate closed ⇒ logits identical to NO_MESSAGE, receiver OOD 0.5–2.3 %, reload bit-identical, message CKA to receiver 0.13–0.51 (no private-state copy), no collapse (min dim sd ≥ 0.35, effective rank 8–11 of 32).

**Gate G-CALLOSUM-UTILITY-002 (L1): FAIL on all 8 tasks.** EXACT wins every task on utility per byte (numbers are 16 B, a tone sentence ~30 B vs 64 B latent), and the sender's own label word (SYMBOLIC, ~7 B) matches LATENT on tone/certainty. `B3_LATENT` stays `unavailable`; L2 is not unlocked.

**Latency.** Bridge 1.2 ms per item (numpy, CPU) vs receiver re-prefill of a span 0.10–0.23 s; latent would win on latency, but that is not enough for the gate.

**Claim limits.** Receiver-adapter read only (no backbone injection), synthetic labels, oracle EXACT spans, CPU cloud not Redmi. Where latent could still win: content with no short exact or symbolic form (mixed graded states, style), or when exact span selection itself is costly. Example bridge (gist/tone) saved here for `:doctor` format checks.
