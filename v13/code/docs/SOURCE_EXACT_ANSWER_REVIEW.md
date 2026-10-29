# Run97 — Explicit deterministic SOURCE_EXACT budget answer (review-only)

This is an **offline, human-triggered** way to answer a narrow question from a real, already verified F1/F5 source, without asking the C3 language model to reproduce a number.

```bash
cd v13/code
python -m scripts.source_exact --home "$HOME/v13" --query "What is the budget for Project Elyra?"
```

With a persisted human correction `Project Elyra budget = 615 Euro` in the active session, the only permitted factual output is `Project Elyra budget: 615 Euro.` and a JSON status `FINAL`, `mode=SOURCE_EXACT`, `model_called=false`, `native_calls=0`. The exact source and session are rechecked immediately before egress. Without an authorized source, with a conflicting, corrupted, cross-session or revoked correction, the lane refuses; no source value is invented.

The existing live `:verified` still only reports READY/CLARIFY and does not answer. Run97 is a separate explicit command, not a change to Runtime._turn or a general retrieval engine. It cannot install a model or override an active Store lock. This improves narrow factual utility without claiming native C3 quality, JEPA, STEP2, B3, Body-JEPA, LP3, Redmi or whole V13.
