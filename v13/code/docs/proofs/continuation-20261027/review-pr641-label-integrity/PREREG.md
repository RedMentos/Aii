# Independent GPT review of Claude PR641 — exact route label integrity (2026-10-27)

Base: Claude PR641 `claude/project-thread-h02m13` at `bc0703f4fbfb794b23ffc49ac8a7cb6074903bfa`. **Review-only child, not Codex Run643 integration.** File ownership: `v13/code/v13/learning_worker.py`, new `tests/test_review_pr641_exact_route_labels.py`, scoped CI/evidence only. Do not alter registered Z6i/Z6i2 cohorts, their hashes, model embeddings, fixed word features, relative gate thresholds or human rule semantics.

## Concrete regression risk
Claude PR641's `train` uses `np.asarray(inp['labels'], dtype=int)` and coerces `scaffold_labels` similarly. That accepts numeric strings, booleans and fractional floats as if they were explicit human 0..3 route decisions. The Codex integration chain already has `exact_route_labels` with type-exact checks; this Claude chain diverged before that guard.

## Prospective RED/GREEN
Reject invalid explicit `labels` with `ValueError` for `0.9`, `'2'`, `True`; reject invalid scaffold `True`. Preserve valid Python/JSON integer lists, 0..3 only, and 20-item training gradient/checkpoint positive control. Run focused route-word tests and full available software suite on this Claude branch, privacy scan relative to the reviewed base. Preserve original RED and raw evidence, then patch only label validation. **No native model, Redmi, authority or whole-system claim**. If full suite cannot run due environment, record exact failure and continue other independent work.
