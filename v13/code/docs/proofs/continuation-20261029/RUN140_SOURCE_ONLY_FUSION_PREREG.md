# Run140 prereg — deterministic source-only B1/B2 fusion control (not a new native cohort)

Date 2026-10-29. Owner `codex/v13-run140-source-only-two-body-control-20261029`. Exact base Run138 PR #1039 at `61b498ae2f7499740acdf32ebb6935b64469b474`, independent of concurrently reviewed Run139 PR #1040. Frozen native Run116 source SHA256 `c0cd539ec28f9583abe25c93f48871597df6758c442782eb6fedd56ad612105f`, tool SHA256 `e90c23fd909dc0e138312f6802a05a3377f451f6675a496c1d4b1f1b19847ac0`; original model/seed/fixture unchanged. Run138 original artifact SHA256 `749f6559aaee371d17ffe512d5baa0aa8ea33a322e5f7ba9001c34b0659733da`, 51/51 outer and 29/29 nested SHA256SUMS verified, all exits zero, 2813 full OK (8 skipped).

## Question and fixed controls

Can the *existing verified* B1 option quotations and B2 earlier-rule quotations drive the existing deterministic eligibility reader/recipe without **any** C3 extraction or new native calls? This is a source-only **control** for attribution, not a proposed replacement for C3 language and not a fresh STEP2 utility proof. Source row must be hash-bound, each evidence span matched to fixture source SHA256 and exact offsets, every B1/B2 verified quote a substring of those spans. Never use analyst hypotheses, oracles or unverified quotations to choose an action. B1-only, B2-only, both_none, both_exact, both_control, same_policy_dual, prompt_only_dual must all be retained. Missing options/rules => UNKNOWN/ABSTAIN; never guess.

Use unchanged `v13.agi.eligibility.fixed_read` and `decide` on verified quote texts. Current source wins over historical quotes. This control intentionally does **not** solve the separate Run139 conflicting-rule ambiguity; `fixed_read` itself returns None for conflicting quote values. Do not activate in runtime. Compare per-fixture action and full decision score against frozen oracle **only after** generating all candidate outputs. Preserve original native outputs and hash manifests.

## Post-observation disclosure

Before this prereg a separate minimal standard-library exploratory parser was run over the original 42 source rows (not the exact V13 reader): it suggested full source-rule+option coverage for Delta/Epsilon/Fornax in `both_exact` and `both_control`, no coverage for Atlas/Borealis/Cygnus, and zero complete B1-only cases. These are post-observation hints, NOT preregistered fresh utility or verified `fixed_read` results. The original Run138 composed posthoc results are 3/6 full exact in both_exact and both_control, 0/6 in B1-only. Any agreement is diagnostic, not evidence of timescale-specific or unique B2 learning.

## Acceptance

Implement isolated `scripts/step2_source_only_fusion_control.py` with frozen 42-row replay, all row/source hashes, source-only verified quote gate, explicit ABSTAIN status, no oracle read until after the decision, no wrong committed. Add focused synthetic source spoof/conflict/missing-body tests, original raw replay and comparison with composed source-repair report; all original negative gates preserved. Branch-only exact-head Linux CI: original 29 raw hashes, source hashes, focused/full tests, privacy/diff, closed SHA256SUMS, independent raw review. Never claim native inference or Redmi. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.

If source-only control ties dual native variants, record that it cannot demonstrate B1/B2 learned complementarity. A useful next *fresh native* experiment must compare genuinely independent source policies and controls with registered seeds and held-out cases, rather than promote this posthoc result.
