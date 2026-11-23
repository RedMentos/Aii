# Run33 preregistration — finite-confidence three-organ vote SHADOW wiring

Owner: GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run32 PR #1359, exact starting HEAD `550185a74e9daddaea27860f6244c1209d376af2`. No edits to Run32 prereg, cohorts, seeds, models, workflows, World-JEPA, or current native owner. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; original frozen AG12 solver blob `66a9419143c456f01747b4796fb327b3b36711b3`; Run31 finite confidence helper blob `46982818f6c6078d823c97388c1a4ec250d82e14`.

## Problem and hypothesis (registered before source)

Run31 proved a **software-only** witness: original AG12 `confidence` maps NaN and +Inf primary token confidence to 1.0; isolated `safe_confidence` rejects them. Run27 closed native ZIP contains final vote rows but **does not retain per-organ token-confidence raw metrics**, so actual malformed native-metric incidence cannot be inferred from those rows. This package tests whether the isolated finite helper can be wired through the actual `BodySolver.ask -> batch -> combine` interface without editing original solver or changing valid finite results.

## Intervention and frozen checks

Add isolated subclass `FiniteConfidenceBodySolver` in `v13/code/v13/agi/solver_confidence_finite_vote_candidate.py`, overriding only `ask` and preserving original generation arguments, deadlines, cancellation, extraction, and inherited `batch`/vote path. Use Run31 `safe_confidence` only for token-confidence conversion; do not monkeypatch original solver, Store, runtime, training, or source/model/seed pins. No production activation. New focused tests with fake runners: (1) valid finite single- and multi-role parity against original; (2) NaN/+Inf/boolean/invalid-priority values cannot vote as certainty; (3) conflicting answers show an invalid primary metric cannot dominate a valid voter; (4) runner arguments, cancellation/deadline, error and original behavior remain intact. Run original Run31 and AG12 regressions too.

Verification: isolated Linux software CI, exact source blob pins, privacy/diff checks, closed raw SHA256SUMS; all stage exits must be zero. CI is **synthetic mock software evidence only**. Native disjoint confidence incidence and calibration study needs separate preregistered run after the current Run32 heavy owner ends, and requires per-role metrics explicitly recorded in that *new* run. Original Run27 raw, cohort and votes remain immutable.

## Binding negative gates

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no proven native invalid-metric incidence, no Redmi measurement, no learned German transfer, no live JEF, no whole-system completion. No merge/auto-merge.
