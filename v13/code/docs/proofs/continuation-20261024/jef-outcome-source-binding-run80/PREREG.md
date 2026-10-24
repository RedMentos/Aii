# Run80 prereg — JEF fast-head outcome source/label integrity

2026-10-24. Base Run79 PR112 `66c525f1b380162610067ae5c29b4f0fd66c11fb`.
Owner: `v13/code/v13/jefoutcome.py`, `v13/code/tests/test_jefoutcome.py`, and new Run80 evidence only. No changes to other owners, model artifacts, native jobs or registered cohorts.

Problem: `jefoutcome.training_rows` checks that an outcome `source_id` exists and is not deleted, but never checks that its content matches the persisted `value` nor that the source kind is `OUTCOME_SELF_LABEL`. A stale/tampered state label can therefore be used for head learning under a different, still-valid source. This violates source-bound JEF self-learning and the lower-than-human evidence hierarchy.

Test-first expected RED: a stored outcome label whose value is changed without changing its source, a source-id replaced with a same-text USER source, or a corrupted source blob must be excluded from `training_rows`. Unmodified, explicitly enabled `learn` outcome rows must remain trainable; human labels still take precedence. Do not grant new learning rights.

Fix: for each candidate, require a nondeleted source of the exact outcome authority kind and validate full-extent `read_source` (hash+blob+chars) equals the stored outcome value. Treat any missing/invalid source as no training row; no synthetic substitute or silent relabel. Run existing 367-test Linux CI and official privacy scanner; preserve RED/GREEN raw logs. No native model or Redmi claim. Original STEP2/B3/JEPA gates remain unchanged.
