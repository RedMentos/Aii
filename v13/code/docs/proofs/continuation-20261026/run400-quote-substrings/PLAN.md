# Run400 — RED-first Run396 source-exact quote substring correction

2026-10-26. Owner GPT scheduled continuation. Base Run399/PR394 `14545c6990141b58c6807b2f3055a88918ab4f79` (stacked review, not main). Own only `v13/code/scripts/run396_step2_pilot_audit.py`, new `v13/code/tests/test_run400_quote_substrings.py`, `.github/workflows/run400-step2-quote-substrings.yml`, and this proof folder. Frozen Run394/395 fixture/model/seed/native source untouched. Run399 original RED must remain preserved.

## Observed independent native RED

Run399 exact-head Actions `40250214439`, job `121340253414`: inherited 44/44 synthetic tests PASS, observed Run395 ZIP `12619659510` SHA `6a0ae4311db51d7165e372b370e57a6faf8223c0e214c87be5f6e1ad5ba46b6f` downloaded and verified, privacy CLEAN; actual Run398 -> Run396 audit returned `PILOT_RED_PRESERVED` with `ValueError: B2 verified quote not exact frozen source`. Raw artifact `12620490121` retained. This is a real independent negative, not a promotion.

Independent read-only inspection of the same SHA-verified ZIP: all 20 quoted B2 snippets failing the Run396 membership test are **literal contiguous substrings** of the registered history/current source, e.g. the first 198 characters of Alder kickoff text. The current test `q in fixture["history"]` checks exact list-item equality, incorrectly rejecting valid source-exact spans. No unsourced B2 quote observed in this pilot, but that must be enforced.

## RED -> GREEN protocol

1. Add isolated regression tests requiring nonempty exact source substrings to pass and fabricated/empty/non-string or case-altered snippets to fail; keep historical-rule provenance separate from correctness of the current action. Trigger RED CI with new tests **before** changing auditor.
2. Narrow auditor correction: `any(q in segment for segment in history + [current])` with nonempty exact string guard. Do not relax source containment or accept model paraphrases.
3. Run all Run394/396/397/398/400 source controls, privacy, then re-audit **the same immutable observed ZIP** through Run398 and unchanged paired scoring. Record both RED and GREEN raw, hashes and measured contrasts.
4. Preserve `STEP2 UTILITY_FAIL`, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0 approval, no Redmi, full-suite RED, V13 incomplete.

## Boundaries

This is an audit false-negative fix, not a change to the native model outputs, registered cohort, rules or utility scoring. Do not rerun native inference or discard Run399 RED. Review exact-substring edge cases and hash-bind raw evidence before any next native cohort decision.