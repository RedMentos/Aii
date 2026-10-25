# Run372 — AG12 native punctuation-only answer must abstain (preregistered)

Parent: Run371/PR366 verified checkpoint `aece4717768c190d6ea3e84b050435ffac1560c3`; review chain, not main. Independent of Run369/PR364 owner (owns native smoke script/workflow only). The original Run369 Actions 40233093916 Linux-native plumbing PASS is preserved verbatim; its solver returned `answer=","`, `confidence_source="mean_prob"` and `confidence=0.0001`, which does **not** demonstrate a meaningful answer or answer-field token confidence. Independent review comment on PR364 already filed.

Owner: `v13/code/v13/agi/solver.py`, new `v13/code/tests/test_agi_invalid_answer_run372.py`, new isolated `.github/workflows/run372-ag12-invalid-answer.yml`, this proof directory. No edits to Run369 owner files, registered AG12 suite/hash, source/model pins, Age/permissions or live tool policy.

Hypothesis: `extract()` accepts punctuation-only output (including valid JSON `{"answer": ","}`) and coerces invalid JSON field types such as `null` into apparent answers. `BodySolver.ask()` then attaches even a high confidence to this non-answer. This makes native smoke falsely appear semantically successful and pollutes AG12 calibration.

RED-first software tests: punctuation-only JSON/plain/truncated output must become empty abstention; a JSON `answer` with non-string value must not be coerced to a valid answer; `BodySolver.ask` must assign zero confidence to invalid answers even when runner reports high token confidence. Valid English word, numeric and signed integer answers and legacy truncated string JSON remain accepted. Existing `combine()` abstention behavior and registered suite unchanged.

GREEN: minimally validate the extracted answer contains at least one alphanumeric Unicode character, reject non-string JSON `answer` fields, and override confidence to 0 with an explicit invalid-answer source when extraction abstains. This is a conservative structural check, not semantic correctness; a nonempty wrong answer can still pass the structural check and is measured by the registered suite.

Evidence: actual Python/SQLite fake-runner tests, inherited AG12 solver and finite-confidence regressions, source-bound RED/GREEN Actions raw receipts, privacy scan and private Library byte comparison. Native Run369 is not rerun or retroactively relabeled; no Redmi/STEP2/B3/JEPA/jepa_weight/whole-V13 promotion. After GREEN, next work should validate field-specific token confidence in a separate pinned native cohort without changing the old cohort.
