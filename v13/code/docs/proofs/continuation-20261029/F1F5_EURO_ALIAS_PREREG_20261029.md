# F1/F5 exact-source Euro spelling equivalence — preregistration (2026-10-29)

Parent: PR #1156 / `56ae98bc153d0897584d38e5d1f80ef610050866`.
Owner: V13 scheduled continuation; review branch only, no production integration.

## Problem / functional objective
F1/F5 source verification accepts integer `Euro`, `EUR` and `€` spellings, but
two independently verified corrections of exactly the same integer Euro amount
are currently treated as contradictory purely because their raw spellings differ.
This forces unnecessary CLARIFY instead of delivering the explicitly requested
`:verified exact` source answer. The original bytes and SourceRef must remain
unchanged; two *different* integer amounts must still veto output.

## Frozen scope and tests (software, not native)
- Change only `v13/code/v13/source_consumer.py` admission equivalence and add
  `tests/test_f1f5_euro_alias_equivalence_20261029.py`.
- Test real isolated Store/Memory/F1/F5 verification with 615 Euro, 615 EUR,
  615 € => ADMITTED; admitted_count=3; exact chosen source bytes match SourceRef.
- Test 615 Euro vs 616 EUR => CLARIFY/CONFLICTING_AUTHORIZED_SOURCES.
- Test `:verified exact` equivalent sources => FINAL_SOURCE_EXACT without C3,
  preserving source spelling, native_calls=0 and learned=false.
- Run focused existing source-consumer and verified-budget suites, Python compile,
  public repository privacy scan, diff whitespace scan, Canon blob check.
- Expected original negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL,
  Body-JEPA unavailable, LP3 FAIL, World-JEPA utility unproven,
  `jepa_weight=0`, Redmi unmeasured, full V13 incomplete.
- No new models, downloads, weight changes, user-source hashes, cohort changes,
  Age0 authority, learning rights or autonomously executed tools.
- A failure must remain visible in CI raw artifacts, not be relabeled PASS.

## Limits
This is a deterministic F1/F5 source-consumption improvement in an opt-in
operator lane, not evidence of native C3 learning or general numerical language
understanding. No grouped, decimal or foreign-currency amount is admitted.
