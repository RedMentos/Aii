# Run11 C3 explicit numeric-answer prompt candidate prereg — 2026-10-28

Owner GPT-6. Review-only child of #848 at `db7702f151aa951a6f4293f98585687e6ca9c8ae`. Do not edit #848 owner, #845 C5 runtime, frozen source-handoff cohorts, main, model catalog, seed or approval/learning gates. Baseline `v13/code/v13/prompts.py` Git blob `a74d7517a7ab70e801e177b58da057e57fd3460c`. This is a **new candidate prompt cohort**, not an update to any registered baseline score.

## Actual failing native witness

Pinned AG0-only native 40633577048 at `431ca3c5ecab7ca16ff75238e61afb6955b29378`, artifact 12792223727 SHA256 `b23586075a8c10890dd87b31bd01d6fb64e7109c71a32a656e681851c0e03e73`, CRC and 21 internal hashes valid, private Library byte-exact backup. JEF C2+C3 no-B 8/8 and STEP12 8/8 structural PASS, but fixed public `ask 'Budget 120 Euro. Berechne die Hälfte.'` returned `The calculation yields the requested amount based on the given value.` — no 60; overall workflow RED by `PUBLIC_ARITHMETIC_60_MISSING`. No tools were approved, and the answer cannot be patched by silently using calc.

## Narrow candidate and falsifiers

Add one concise instruction to both EN and DE **system prompt** strings only: for an unambiguous numerical calculation, state the actual numeric answer, never a vague description; if unable to calculate, say so rather than pretending. Do not supply the answer 60 in the prompt, hard-code any arithmetic rule, use an external tool, change answer_language default, edit C5 or C6, or alter Age0 permissions. Unit tests verify both languages and exact source isolation. Run focused/full Linux software regression, then fresh pinned Linux native `v13 ask` with same public 120/2 and the current catalog, compare to baseline 40633577048 as a **nonpaired** observation; record exact output and model hashes. Optional unsupported-source C3-only fixture remains a separate negative reliability witness.

Success for this narrow candidate: explicit 60 appears in the actual final answer, not merely in a test prompt or log, and no unauthorized tool/age change. Failure: generic answer, wrong number, or output without 60. A single correct arithmetic answer would not prove general numerical reliability or whole V13. Preserve original failure, negative STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY. No native run before software focused/full GREEN and no competing native/model owner. Remaining platform budget UNKNOWN.
