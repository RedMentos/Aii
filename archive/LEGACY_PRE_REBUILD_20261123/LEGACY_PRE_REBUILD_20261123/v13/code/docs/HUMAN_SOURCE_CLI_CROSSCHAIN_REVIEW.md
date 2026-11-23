# Run96 — Human source to offline CLI, same persisted Age0 home

This is the combined user workflow **after** Run94 and Run95 exact source imports have independently passed their corrected original raw tests. It is not available on the older `main` branch.

In the interactive local V13 console:

```text
:source budget Elyra 615
:source budget Elyra 615 --confirm
:verified What is the budget for Project Elyra?
```

The first command is a no-write preview; the second records a human F1/F5 source in the current session with `permission=record`. The third is a model-free READY preflight, **not a generated answer**. Exit the interactive console before using the offline CLI so the Store lock can be acquired:

```bash
cd v13/code
python -m v13 --home "$HOME/v13" source-answer "What is the budget for Project Elyra?"
```

That command must return READY from the exact same persisted memory and SourceRef. An explicit `--native` is a separate human action and requires the current catalog-pinned C3 model and native runner already installed; without them the command refuses with `C3_MODEL_NOT_PINNED`. A wrong-project or out-of-scope query refuses without loading C3 even when `--native` is specified.

To revoke, reopen the local console and use `:forget <Memory-ID> --confirm`; the offline CLI must then return CLARIFY and zero native calls. Backups remain separate and may still contain older copies, as the canonical forget contract states.

Run96's test uses an **actual separate Python process** with the same on-disk home and verifies source continuity, Store lock, no native model, and forget. Run93 separately tests one real native Linux C3 answer, not general factual quality. No STEP2/B3/Body-JEPA/LP3/Redmi/whole-system promotion.
