# Run368 — AG12 holdout cannot be laundered inside training strings (preregistered)

Parent `codex/fullsuite-after-run366-20261025` @ `9df12a9d9032805aab7921da9b6c104ccfb3e654` (Run367 full-suite measurement in flight; no shared source edits). Ownership: `v13/code/v13/agi/generality.py`, `v13/code/v13/agi/teacher.py`, new `tests/test_agi_embedded_holdout_run368.py`, isolated workflow, this proof directory. No modification to registered suite seed, item prompts, answers, IDs, hash, native/model artifacts, approvals or age.

## Source-level defect
`GeneralityEval.guard_training` hashes each entire normalized candidate text and compares only with registered exact holdout prompt digests. Wrapping an unseen holdout prompt in an instruction/answer string changes the whole-text hash and bypasses the training gate, despite the same exact holdout task appearing verbatim. `TeacherDistillation.dataset` currently guards only `trace.prompt`, but returns `teacher_answer`, `reasoning` and `rejected` for distillation; those can contain a holdout prompt too. This is benchmark contamination, not evidence of model intelligence.

## RED-first actual Runtime tests
1. `guard_training` rejects an exact unseen prompt even when wrapped in instruction and answer text or normalized case/whitespace, and still accepts ordinary seen/nonholdout text.
2. `TeacherDistillation.dataset` rejects an ordinary prompt whose local fake teacher answer includes an exact unseen prompt, without making any native/cloud request.
3. The same guard covers teacher reasoning and rejected own-answer fields, while a safe trace remains usable.
4. Existing `test_agi_solver`, `test_agi_live`, `test_agi_trainers` continue passing.

GREEN requires a bounded current-suite normalized holdout substring check while retaining stored hash equality, and checking all returned teacher training fields. RED and GREEN exact-head Actions with raw evidence, SHA, privacy and private Library backup. Do not promote STEP2/B3/Body-JEPA/jepa_weight or claim a real learning gain.
