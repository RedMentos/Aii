# Run14 German earlier-rule source cue — preregistration, 2026-10-28

Parent: review-only PR #925 Run13 guard at `5a571e611e58d8f7e9c4897ee0008e707ce42c8a` (its final full CI pending at branch creation), itself child of independently audited #924. This is a separate source-only candidate, not a production merge, and does not modify Run12b/Run13 owner source, frozen Runtime, original TP/s27 native corpus, model/seed hashes, or gate rights.

## Problem
Run12b's older-rule lexical cue matches English `earlier|prior|previous` and `rules`. A German request for `frühere Regeln` leaves B2 offers newest-first. Under the unchanged 768-char cap, a supplier sheet can crowd out the older binding note. German must not be treated as a proven learned skill; this is a fallible source-pointer selection experiment.

## Planned candidate and safety contract
Add only `scripts/run14_b2_german_prior_cue.py`, `tests/test_run14_b2_german_prior_cue.py`, independent source-only CI and additive handoff. Detect explicit German earlier-rule intent without translating facts, values or source text. Refuse to prioritize when the user explicitly supplies current/revised binding rules. For each item *within* the original newest `slots` horizon, use the Run13 verified, single-project selector as a preflight; score exact source excerpt for **presence of rule words only** (`Regeln`, `Budget`, `Frist`, `Lokalpflicht`) and sort eligible offers stably before the unchanged final cap. Re-read/validate sources on final selection. No oracle, no numerical decision, no cross-project match, no new authority, no model call or training.

## RED-first / success checks
(1) Under a deliberately binding 450-char cap, German earlier-rule request should prioritize the older Aquila note where current Run13 order picks a recent supplier sheet; (2) English earlier-rule behavior unchanged; (3) current revised German rules do not prioritize old; (4) multi-project and mixed-project source refused; (5) tombstone and malformed refs refused before source use; (6) slots, session/model and cap unchanged; (7) no gate promotion. Preserve RED, then source-bound focused/full software, compile/privacy/diff, SHA-closed raw, private readback. A selected note is not a B2 native quote, C3 decision, or STEP2 utility improvement.

## Original gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 incomplete. Owner Run14 German cue; exact next step tests-before-code, then isolated candidate and independent CI. Remaining execution budget UNKNOWN.
