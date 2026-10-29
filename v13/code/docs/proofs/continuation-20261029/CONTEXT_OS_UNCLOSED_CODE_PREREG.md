# Context OS unclosed Markdown code-span fail-closed guard — prospective prereg (2026-10-29)

Owner: GPT-6 independent Context OS package. Parent exact commit `48a58ca8ca49c0b908509e04081cf9fc132017fd` (PR #1083 review chain), no edits to JEF/AG6/native models. Existing Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` remains unchanged.

## Observed reproducible loss, before code edits

In `v13/context_os.py`, `compress` uses `exact_spans` with regex `CODE` matching only **closed** backtick spans. For an old turn beginning `Intro.` followed by an **unclosed** Markdown fenced code block and a long paragraph, the unclosed block is not in `exact_spans`; the original `compress` returns `ok=True` and only `Intro.`, silently omitting the source code from the active view. This contradicts §8.3–8.5 exact code/quote preservation and the existing unmatched-quote RAW fallback. Reproduction is pure software, not native evidence.

## Narrow fix and tests

Add a conservative read-only Markdown-backtick balance check before Context OS compression: when a fenced block or inline code delimiter is left open, keep the entire text RAW (`ok=False`); never fabricate closing delimiters or truncate a potentially literal code span. Preserve the existing `CODE` extraction for valid closed spans and unchanged normal compression. Tests must cover unclosed fenced Python, unclosed inline code, valid closed inline and fenced spans, mixed closed+unclosed delimiters, long text and Unicode. Also test a Context OS plan retains the unclosed-code turn RAW rather than claiming exact-span recall success on truncated text. Avoid changing runtime authority, memory source, Context OS ACTIVE defaults or compression thresholds.

## Proof and gates

Run focused Context OS unit tests plus full software suite on exact source head; preserve raw logs, hashes, privacy and diff check in GitHub Actions. Any RED stays RED. No model/native/Redmi claims; no frozen P0X/P2X cohort modifications or holdout tuning. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, AG6 unapproved, Redmi unmeasured, V13 INCOMPLETE. Next independent package after verification should address another substantive canonical path, not repeat this guard.
