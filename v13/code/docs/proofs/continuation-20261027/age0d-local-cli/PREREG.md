# WP-AGE0d local CLI prereg — 2026-10-27

Exact parent `151f66df9b068c85d0460bdb3adbf69955a7126d` (PR #755, full source-wide software run 40562100437 success on its PR merge; no runtime integration). New review-only branch `assistant/v13-age0d-local-cli-20261027`; not main. This file is committed before CLI source and tests.

Goal: make the narrow answer-aware arithmetic diagnostic **locally runnable** for human/developer testing without editing frozen runtime or granting any `:self correction deliver` authority. Implement a standalone standard-library CLI that accepts exactly one explicit `--stdin-json` object with only `question` and `answer` strings, or `--demo` synthetic mode. No arguments carrying private text, no model calls, no file/network writes, no persistence or unsolicited messages. Hard input size bound 4096 characters; malformed JSON, extra keys, missing fields or oversized input fail closed with a sanitized ABSTAIN report and nonzero exit. Never echo raw question/answer; output structured status/expected/observed numeric values only. CLI default without a mode must do nothing and return nonzero.

Frozen checks: correct and mismatch stdin cases preserve `CORRECT`/`MISMATCH`; malformed JSON, oversized input, extra keys and invalid types abstain; demo is synthetic; no text echo; command exits 0 only for structurally valid input (even when arithmetic abstains), 2 for invalid transport. Focused tests, Python compile, privacy scan, diff check and closed raw exits. Full source-wide software suite can be run separately; no native/Redmi claim.

No changes to `v13/code/v13/`, no live hook or user communication. Original AGE0c STAY_SHADOW, LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight0, Age authority0, Redmi unmeasured, V13 incomplete.
