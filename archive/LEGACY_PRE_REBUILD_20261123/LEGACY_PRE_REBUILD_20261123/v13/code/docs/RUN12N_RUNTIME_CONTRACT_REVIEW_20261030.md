# Run12N independent runtime-contract review — candidate, not original data

Parent review-only PR #1271 exact HEAD `afc6308fa2e57027f8079228f6fe20dc3083e92a`. Original Run12N native Actions `41060739689` was launched on that unchanged HEAD; preserve its outcome and original raw even if RED. This candidate must not retroactively alter the original run.

## Concrete source counterexamples found before native results

Original Run12N `fresh_turn` called `Runtime(home, turn_cfg)`, although actual Runtime signature is `Runtime(home, notify=None)`; config would be treated as notification callback, not config. It called nonexistent `runtime.start()`, passed unsupported `session_id` to `runtime.submit(text)`, treated submit's event-id string as an audit dict, and referenced nonexistent `frozen.release_rows`. Original synthetic tests mocked the frozen evidence and never exercised this actual Runtime API. Additionally `zero_offer_witness` compared release `role` (scalar string) with `frozen.ROLE_BY_ROUTE[route]` (tuple), making real final releases fail while the synthetic test passed with an artificial tuple role.

## Candidate fix / test contract

On this child branch, use frozen Run11V's isolated Store+symlinked pinned models, `Runtime(home)`, `runtime.submit(text)` -> `audit_event(store,event_id)`, bounded `idle()`, exact source packet lookup, original preclose write before `close()`, postclose `runtime.pool.release_history`, and captured Needle process/pid/reap. Observer remains OFF for all arms. New tests assert exact Runtime signatures, call AST shape, source-audit path, and reject tuple-valued synthetic release roles. Preserve frozen fixture seed197 SHA256 `94cce591dcf9ade126cfdb2d32261543c8334523b6d268295759d9ef7b691df1`, original scorer, Runtime, model pins and negative gates. This is a **software candidate only** until exact-head tests pass; native rerun requires original run terminal, raw preservation and independent review.

Next exact command: launch source-only pinned CI for candidate; inspect original `41060739689` after terminal and original ZIP; never run competing heavy job. Then decide whether technical rerun of same preregistered cohort is legitimate (no model answers were produced) or needs new disjoint preregistration. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight 0; Redmi UNMEASURED; whole system incomplete.
