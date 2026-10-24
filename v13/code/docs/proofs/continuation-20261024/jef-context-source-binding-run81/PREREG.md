# Run81 prereg — JEF fast-head decision-context source integrity

2026-10-24. Base Run80 PR113 `1434c51fdb704d16daf2739948385de22736475d`.
Owner: `v13/code/v13/jefoutcome.py`, `v13/code/tests/test_jefoutcome.py`, `v13/code/tests/test_jef_outcome_lineage_run69.py` (synthetic fixture contract only), and Run81 evidence. No other owner's files, model downloads, native jobs or paid provisioning.

Problem: Run80 verifies the *label* SourceRef but `training_rows` still trusts `ExecutiveDecision.context_ref.sha256` without reading the underlying source. A revoked or corrupt context can therefore train a C2 fast head. `learning.decide` uses the original user event SourceRef as context for fast heads; it must remain source-valid and identical to the event and decision provenance.

Test-first expected RED: deleting the original event/context source, corrupting its blob, or changing the ExecutiveDecision context SourceRef to another same-content source must each suppress the self-label training row. Unchanged valid source must still train; explicit human precedence and record-only default unchanged.

Fix: verify complete decision context SourceRef through `Store.read_source`; for fast heads require it to equal the event envelope's SourceRef and be included in the ExecutiveDecision provenance. Reject malformed or missing links, no fallback to matching text/hash alone. Existing Run69 synthetic SQLite fixture will be updated to represent actual event/context source fields if its minimal schema cannot satisfy the strengthened contract; preserve original fixture errors. Run 370+ Linux tests and official privacy scan, preserve raw RED/GREEN evidence. No native/Redmi or STEP2/B3/JEPA gate promotion.
