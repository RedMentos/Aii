# B3-H3 L1: receiver-adapter-only latent read, cloud measurement 2026-10-09

Script: `code/scripts/b3_l1_bench.py`.

**Setup**
- Sender: B1 LFM2.5-1.2B, mean-pooled final state (2048 dim).
- Receiver: B2 Qwen3.5-0.8B (1024 dim).
- The B3 message is the sender state, PCA-projected to rank 16. The receiver gets a small logistic readout; nothing enters the backbone.
- 480 synthetic items, 10 paired seeds, partitions fit/select/test 60/20/20.

**Test accuracy** (mean over 10 seeds)

| Task | Chance | NO_MESSAGE | EXACT | SYMBOLIC | L1 | L1 shuffled | L1 random |
|---|---|---|---|---|---|---|---|
| sum_ok (is the stated total correct?) | 51 % | 63 % | **99.6 %** | 63 % | 63 % | 64 % | 62 % |
| max_item (largest of 3 items) | 34 % | 69 % | **100 %** | 70 % | 72 % | 68 % | 69 % |
| topic (gist control) | 35 % | 100 % | 100 % | 100 % | 100 % | 100 % | 100 % |

Paired L1 − NO_MESSAGE:

| Task | Mean | SE | L1 wins (of 10) |
|---|---|---|---|
| max_item | +2.5 points | 1.4 | 6 |
| sum_ok | −0.2 points | 1.1 | 5 |

**Result.** The sender's latent state carries at best a weak extra signal (max_item, not significant) and nothing for arithmetic. The exact channel solves both detail tasks almost perfectly. Under G-CALLOSUM-UTILITY-002 / B3-H9, LATENT must beat EXACT, so L1 fails the gate: `B3_LATENT` stays `unavailable`, and SOURCE_EXACT remains the right channel for detail.

**Claim limits.** These are synthetic detail tasks with mean pooling and a linear readout. A trained selector/pooler (B3-H2 message subspace) or tasks without an exact equivalent (style, uncertainty, intent) could look different; that would be the next L1 attempt.
