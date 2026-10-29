# Run139 prereg — source-ambiguous eligibility rule fail-closed candidate

Date 2026-10-29. Owner: `codex/v13-run139-eligibility-ambiguity-20261029`. Base: Run138 PR #1039 exact `61b498ae2f7499740acdf32ebb6935b64469b474`. Do not edit frozen `v13/code/v13/agi/eligibility.py`, production runtime, registered model/seed/fixture, or existing raw. This is an isolated default-off candidate.

## Independently reviewed base evidence (before this prereg)

Run138 Actions `40820205991` completed success at exact base HEAD. Downloaded original artifact `12873824708`, ZIP SHA256 `749f6559aaee371d17ffe512d5baa0aa8ea33a322e5f7ba9001c34b0659733da` matching GitHub digest, ZIP CRC clean; 51/51 outer and 29/29 nested SHA256SUMS verified independently, all recorded *_EXIT files zero, focused and full exits zero, full `Ran 2813 tests ... OK (skipped=8)`, original Run116 42-row raw intact. Software-only replay: 42 rows, 7 repaired rows, 25 fields, 40 literal project aliases, 9 exact gains vs original, zero wrong committed; after repair `both_exact=both_control` (3/6 exact, mean utility 0.791667), so no demonstrated unique two-body complementarity. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; whole system INCOMPLETE. This does not establish native/phone/production promotion.

## Source-observed failure and precommitted hypothesis

Frozen `v13/code/v13/agi/eligibility.py` at Git blob `e1f1a2d09a614378a75e397819fdce96a46de22d` implements `decide`: `override=stated_values(rule,current)`, rejects only when extracted `v not in override`; it **accepts** a value when the current text states two different values including `v`. Similarly it accepts an extracted value supported by one of two contradictory historical verified quotes when current has no rule. Thus a source-ambiguous budget/deadline/locality can yield a committed A/B/NONE instead of UNKNOWN. This is a static code finding, not yet a measured test result.

Hypothesis: a pure optional `strict_decide` wrapper can keep unambiguous decisions byte-equivalent to existing `decide` while masking conflicting rule fields to None **before** the original recipe. Current source takes precedence only when it has exactly one value. Without a current value, distinct values across verified quotes are ambiguous; refuse. Do not choose a historical revision by quote order (not a trusted chronological proof). Preserve original `rejected` reasons, append deterministic `<rule>:ambiguous_current` or `<rule>:ambiguous_quotes`, and keep `revision` original. Do not grant authority to model hypotheses.

## Fixed acceptance and counterexamples

1. Current source `Budget 100 euros. Budget 50 euros.` + otherwise valid options and extracted budget=100 must produce UNKNOWN, null remaining and eligible, reason `budget:ambiguous_current`. Analogous contradictory deadline and local-only tests.
2. Two verified historical quotes with conflicting budget and no current budget must produce UNKNOWN even if model extracted either value; reason `budget:ambiguous_quotes`. Analogous deadline/local-only tests. Untrusted quotes are NOT authenticated by this wrapper; upstream verified-source gate is mandatory.
3. A unique current rule overrides contradictory older quotes if extraction matches the current value; mismatched extraction remains rejected by original guard. Unambiguous historical quote and no current rule must preserve exact original output. No mutation of caller inputs; nonambiguous output equality.
4. Adversarial same-text two conflicting options is separately investigated; do not claim option ambiguity solved by rule-only candidate.
5. New focused tests and full suite on pinned source head; raw evidence with source SHA, full/focused/privacy exits, original Run116 unchanged and original Run138 negative gates. No new native calls, no Age promotion, no STEP2 promotion. A test failure is RED and must be preserved.

Next: add isolated script `v13/code/scripts/eligibility_rule_ambiguity_candidate.py`, focused tests `v13/code/tests/test_eligibility_rule_ambiguity_candidate.py`, and branch-only GitHub Actions workflow. Keep all changes additive and default-off; independent raw review before integration.
