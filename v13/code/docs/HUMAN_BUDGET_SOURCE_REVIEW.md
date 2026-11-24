# Run95 — Explicit human F1/F5 budget source (review-only)

The human operator can record a narrow source without first asking a model to answer. Example in the V13 local text console:

```text
:source budget Elyra 615
:source budget Elyra 615 --confirm
:verified What is the budget for Project Elyra?
```

The first command **previews only** (`CONFIRM_REQUIRED`); the second commits `Project Elyra budget = 615 Euro` to the current session as a real user-authored F1/F5 `HumanDecision` / `MemoryRecord` with `permission=record`. The third command returns `READY` with SourceRef, **not an answer** and not a native model call. `:forget <Memory-ID> --confirm` revokes it. A later explicit value for the same key supersedes the active old value using the existing memory rules.

This deliberately supports only `ProjectName` (ASCII letters followed by up to 39 ASCII letters/digits/`_`/`-`) and a whole nonnegative Euro amount up to nine digits. No automatic ingestion, no general fact parser, no global memory write, no tool invocation, no weight update and no semantic interpretation by C3. It requires a human TTY command, `--confirm`, idle Age0 RECORD_ONLY and the unchanged user/age/approval gates. Use the independent Run94 CLI review to perform an offline source-answer preflight or explicitly opt into native C3; native usefulness is evaluated separately in Run93.

Source and tests: `v13/source_record.py`, `tests/test_run95_human_budget_source.py`. Prereg: `docs/proofs/continuation-20261028/RUN95_HUMAN_BUDGET_SOURCE_PREREG.md`. This is software functionality only; no STEP2/B3/Body-JEPA/LP3/Redmi or whole-system acceptance.
