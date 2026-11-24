# WP-S7: Sleep with offline compute

Module: `code/v13/sleep_offline.py`, phase `SLEEP_A_OFFLINE`. It runs in `:sleep run full|a` and in autonomous full sleeps, right after Sleep A, unless Sleep A was interrupted. It is skipped in YELLOW and RED, and it checks for user input, deadline and resources between steps.

1. **Day digest (re-encoding).** For each session, the turns since the last digest are compressed extractively (`context_os.compress`). Exact spans such as numbers, dates, code and URLs survive verbatim. Lineage is checked through `history.native_history`, so deleted sources never appear. The digest is incremental and capped at 96 entries per session, with fact authority 0. View it with `:sleep digest`.
2. **Predictor update.** The fast-forward predictor (WP-F) now keeps a buffer of the last 256 outcomes. Sleep runs 3 low-rate NLMS passes over the older 80% and keeps the new weights only if the error on the newest 20% does not rise (`KEPT`/`REVERTED`).
3. **Context→LoRA (TTT) candidates.** For each FINAL model answer, the pair (digest of the 4 previous turns, question) → answer is written to `exports/sleep-ttt-candidates.jsonl` with status `CANDIDATE_NOT_TRAINED`. No weights change here. It respects `:pause training`, and system-initiated sleeps need the Age right `small_shadow_update` (Age 0).

## Digest in the live context (measured, default on)
The digest of turns that have dropped out of the history window (`history_turns`) enters the system prompt as a COMPRESSED layer. Lineage is re-checked on every turn: a source deleted after the sleep never appears. It is switchable with `:ctxos digest on|off` and is recorded in turn meta as `digest_lines`.

Cloud bench (`scripts/digest_context_bench.py`, `bench-results/digest-context-20261009/`): 24 synthetic chats per condition, 4 visible turn pairs, greedy decoding, exact value in the answer.

| Model | Old fact, no digest | Old fact, digest | Fact in window, no digest | Fact in window, digest |
|---|---|---|---|---|
| C3 LFM2.5-230M | 0 % | 79 % | 79 % | 83 % |
| B1 LFM2.5-1.2B | 0 % | 88 % | 75 % | 79 % |
| B2 Qwen3.5-0.8B | 0 % | 92 % | 71 % | 75 % |

Most remaining misses are reformatted dates ("December 14, 2026"), which still count as misses here.

The first digest format (`U: … | A: Noted …`) hurt answers about facts in the window (C3 79 → 38 %, Qwen 71 → 46 %), because the small bodies copied the repeated acknowledgement. The current format (`- user: …`, the answer only when it carries exact content or more than 60 characters) shows no harm. The sample is small (n = 24); a long-chat measurement on the Redmi is still open.

## Claim limits / open
- The digest is extractive, not a model summary. A native C3 summary in sleep would be the next step, but it costs RAM and time on the Redmi.
- The digest changes the system prompt once per sleep, so the cache prefix stays stable between sleeps.
- The TTT candidates are self-labels: own final answers, not human labels. The WP-I train runner may use them only behind its retention gate and with human approval.

Tests: `tests/test_sleep_offline.py` (5).
