# Run94 — Offline source-answer CLI (review-only candidate)

Use the **existing** V13 home after stopping the interactive chat. The command requires the real persisted Memory/Store and refuses to initialize a new empty home. It does not change `:verified`, which remains a fast, model-free live operator preflight.

```bash
cd v13/code
python -m v13 --home "$HOME/v13" source-answer "What is the budget for Project Elyra?"
python -m v13 --home "$HOME/v13" source-answer "What is the budget for Project Elyra?" --native --timeout 90 --max-tokens 64
```

The first command does **not** load C3; it returns JSON `READY` (with a verified F1/F5 SourceRef), `CLARIFY` or `NOT_APPLICABLE`. It does not answer the question. The second explicitly requests one pinned, deep-hash-verified C3 native decode; it can return `FINAL` only if the generated answer matches the exact source and the native process is proven reaped. Missing/wrong/revoked/conflicting source, non-Age0 state, unverified model, concurrent running V13 and invalid native output are refused. No model download occurs automatically in this command.

This is a **narrow project-budget source grammar** and a human-triggered offline path, not general factual question answering or a production `Runtime._turn` replacement. Run93 independently evaluates real Linux native answer utility; Run94 tests only software and mocked native flag forwarding. Do not promote STEP2/B3/Body-JEPA/LP3/Redmi or whole V13 from these tests. User rules, approval gates, Age0 RECORD_ONLY and source revocation remain authoritative.

Review branch: `assistant/v13-run94-source-answer-cli-20261029`. Prereg: `docs/proofs/continuation-20261028/RUN94_SOURCE_ANSWER_CLI_PREREG.md`.
