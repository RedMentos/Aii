# Run98 — Human-recorded source, exact answer inside V13

This candidate integrates the independently verified human source and deterministic answer paths. It does **not** make ordinary chat automatically answer from memory; the human explicitly requests the exact source lane.

```text
:source budget Elyra 615
:source budget Elyra 615 --confirm
:source answer What is the budget for Project Elyra?
```

The first command previews without writing. The second records an F1/F5 `HumanDecision` and `MemoryRecord` in the active session, with `permission=record` and no native model call. The third returns `Project Elyra budget: 615 Euro.` only after verified source admission and pre-egress revalidation. JSON reports `mode=SOURCE_EXACT`, `model_called=false`, `native_calls=0`; it is a deterministic quotation/reformatting of a user-provided source, **not C3 reasoning**.

Wrong project, absent/revoked/conflicting/corrupted source, non-TTY origin, active work and out-of-scope questions refuse. `:forget <Memory-ID> --confirm` revokes the answer source; restart does not silently reauthorize it. The existing `:verified` remains a model-free preflight, and `source-answer --native` is a separate explicit offline C3 path.

The scope is one bounded project-budget grammar, not general question answering or automatic learning. Age0 RECORD_ONLY, no weight commit, no STEP2/B3/Body-JEPA/LP3/Redmi/whole-system promotion.
