# Run68 prereg — JEF human RECORD veto for outcome self-labels

Date 2026-10-24. Base PR100 Run67 e6104c8cff892cd110c126fc4f2c13c51fc58a06. Owner: only `v13/code/v13/learning.py` shadow_readout source-label precedence callsite; new tests/evidence under Run68. No edit to Run67 jefoutcome matcher, Callosum, World Model, native, or blueprint.

RED hypothesis: a valid latest human `record` label on a context must block lower-authority outcome self-label for the same context. Run67 currently passes only `learn` human keys to `jefoutcome.training_rows`. The old behavior can therefore admit a self-label despite human RECORD permission. Test human learn, record, absent decision, stale revision. Fix passes all valid human context keys, without changing any training or approval gate.

Evidence tiers: isolated software scratch replay + focused tests; full actual V13 Store and full repo NOT RUN unless checkout obtained. Original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
