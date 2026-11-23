# Run31 — finite AG12 native token-confidence SHADOW candidate verified (software only)

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run30 at `709899cf7832b753c2c344c54fa33f816a6b85b0`. Binding Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Frozen production `v13/code/v13/agi/solver.py` blob `66a9419143c456f01747b4796fb327b3b36711b3` unchanged; original Run24–27 model/seed/source cohorts and native artifacts untouched.

## Reproduced bug and isolated intervention

Original `solver.confidence` applies `max(0., min(1., float(value)))` before downstream AG12 nonfinite veto. Under Python, `float('nan')` and positive infinity are mapped to **1.0**, so an invalid native token-confidence metric can become maximal certainty and potentially distort the three-organ vote. Booleans are also accepted; huge integers can overflow float conversion. This is a **software witness**, not proof that any actual Run27 native output contained malformed confidence.

Added separate `v13/agi/solver_confidence_finite_candidate.py` with pure `safe_confidence`: preserves valid finite probabilities and priority `field_min_prob > field_mean_prob > mean_prob`, but a present invalid primary value returns zero with explicit `invalid:<field>`, never falls back to a lower-priority field or silently becomes certainty. Absent metrics retain historical .5 default. No Store, model, network or runtime integration; `solver.py` remains unchanged.

## Original closed software evidence

Actions **41146065953** terminal SUCCESS at exact source `9c5ad11ab1d229334ad2ec7aac74a5188203da0a`; artifact ID **13020697124**, ZIP SHA256 **`bcf9f1c68953013f9b87e41c77a00bf6e5e08c93954b010147dfc1ce7f2c291b`**. Independently downloaded; ZIP CRC PASS, **16/16** inner SHA256SUMS verified. PINS/VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF all exit 0; **22/22** focused tests PASS (6 new negative/priority/determinism tests plus original AG12 nonfinite and solver regressions). Privacy CLEAN, original solver and Canon blob pins verified. No native GGUF, Redmi or real invalid-metric incidence measurement.

Permitted private Library backup `/V13-Checkpoints/2026-10-31/Run31-AG12-FiniteConfidence/run31-software-41146065953-shabcf9f1c6.zip` uploaded and independently materialized/read back **byte-identical** to original artifact. No rejected Drive destination used.

## Exact next step and gates

Independent review must decide whether to integrate this candidate into `BodySolver.ask` only after the frozen SourceHandoff/AG12 cohort permits a new source-bound branch. Then preregister a **disjoint native** valid-confidence parity/invalid-confidence negative control, compare source-bound outputs and calibration, preserve original Run27 evidence. This package is SHADOW and does not alter current production vote.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no learned German transfer, no Redmi, whole V13 incomplete. No auto-merge.
