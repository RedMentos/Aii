# Run489 — retrospective deterministic JEF fixed-reader shadow replay (registered before script/CI)

**Date:** 2026-10-26. **Owner:** Run489 isolated shadow package. **Base:** Run488 checkpoint `0220824cf54ad9ee549e873303923305ede6eeb5`. **No native/model calls.**

## Binding and scope

- Reuse *unchanged* original Run479 Linux-native 378-row, nine-arm (O/P/S × seeds 20/21/22) safe no-model artifact ID **12633269066**, SHA256 `a87acfa38688e66e603fe9c07cbc0762b231a6eb74527a8010c595e487e46afe`. No cohort, seed, model, prompt or production-runtime modification.
- Frozen six Run394 fixtures: Alder, Beacon, Cypress, Delta, Ember, Fable; seven variants each; **378 rows**. Source fixtures: `v13/code/scripts/run394_step2_fresh.py` blob `fae7aed612108a554d8566b2917ebf31022df423`.
- Existing deterministic JEF reader `v13.agi.eligibility.fixed_read` and `decide`, blob `1778752f4a92de660a48a3c208134ef601bcbb9f`; no model is permitted to interpret rules. Existing exact scoring `v13/code/v13/utility.py` blob `f4a92dab9c4a40761d64394cdca1c052e9a76bfd`.
- Input is only original `step2_{arm}_{seed}.json` source report `consumer_messages` (SHA-bound to the corresponding original `tool_*.json` row), specifically `current_source` and analyst `verified_quotes`. Ignore analyst hypotheses and oracle when generating decisions. The oracle is used **only after** the shadow decision for scoring. Require exact original ZIP hash and Run488 answer audit first.

## Predeclared diagnostics

1. Recompute a fixed-reader decision for each row, preserving original variant and arm; return `UNKNOWN` when a required rule is unavailable. If both option clauses cannot be read exactly, mark `UNSUPPORTED` with utility 0; never fabricate values.
2. Score each answer against frozen oracle using exact 12-field scoring, recording mean utility, exact rate, wrong committed decisions, abstentions and unsupported rows by arm/variant/seed/fixture. Do **not** silently drop unsupported rows.
3. For `both_exact`, separately ablate B1_DETAIL quotes and B2_GIST quotes while holding current source unchanged; compare same 18 seed/fixture pairs per arm. These are **counterfactual shadow replays of frozen quotes**, not native reruns.
4. Check revision precedence (current-source revisions override old notes), source-only provenance and deterministic repeatability. Fail closed on missing/duplicate rows, changed consumer-message hashes, unknown roles, invalid quote shapes, missing required fields or nonfinite scores.
5. Record raw report, exact script/source blobs, CI stdout/stderr, SHA256 receipts, privacy scan and negative gates. Preserve all failures.

**Prior knowledge / limits:** This is a post-hoc analysis after inspecting a few original rows; it is **not blind prospective preregistration**. Earlier Run488 independently showed pointer `both_exact` utility 0.5972, B1-only 0.7037 and B2-only 0.0972, so the original STEP2 complementarity gate remains FAIL. The fixed reader may reveal whether C3 extraction is a bottleneck, but cannot by itself establish neural two-body learning or canonical ten-episode acceptance.

**Locked status:** STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi unmeasured; latent authority 0; whole V13 incomplete. This package is SHADOW and never enables any new tool, action or learning permission.
