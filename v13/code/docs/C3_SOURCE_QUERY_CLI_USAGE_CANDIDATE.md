# V13 Age0 bounded source-backed C3 CLI — review candidate

This is a separate opt-in operator utility. It is **not** integrated into the normal V13 chat `Runtime._turn`, not an AGI or STEP2/B3/JEPA promotion, and not yet measured on Redmi.

Run from the repository root with an **existing V13 home** that already contains a verified F1/F5 human-recorded project budget correction and the canonical C3 model. Do not invent a memory correction by supplying an amount in the command: only the live store can authorize it.

```sh
PYTHONPATH=v13/code python3 v13/code/scripts/ask_verified_budget.py \
  --home "$HOME/v13" --query "What is the budget for Project Elyra?"
```

Default result: JSON `READY` (verified source exists) or `CLARIFY` (missing, revoked, wrong topic, conflicting, invalid session); **no C3 generation**. `READY` returns memory ID, SourceRef and prompt digest, **not a generated answer**.

For one actual local C3 generation, explicitly opt in:

```sh
PYTHONPATH=v13/code python3 v13/code/scripts/ask_verified_budget.py \
  --home "$HOME/v13" --query "What is the budget for Project Elyra?" --native
```

Native is bounded to 64 tokens / 120 seconds by default, seed 13. It requires Age0 `RECORD_ONLY`, `jepa_weight=0`, latents OFF, an idle queue and exact catalog-pinned C3 GGUF with deep file SHA256 verification. It revalidates source after model acquisition and unloads C3. If output does not contain the exact source amount with Euro currency, the output is **suppressed** as `UNVERIFIED_NATIVE_ANSWER`. No downloads or external tools are triggered.

The CLI creates no Runtime coordinator/sleep worker and does not change the operator's sleep policy. **It is not strictly read-only**: opening the existing Store acquires a lock and may perform normal WAL/queue recovery, telemetry cleanup and key-SourceRef maintenance. Do not run it simultaneously with the normal V13 coordinator; exclusive Store locking will refuse concurrent access. Do not use an uninitialized home. A native call may fail or be slow on Redmi until device-specific proof exists.

**Proof status:** Linux software at source `4ee33a8d01418845f38b1344753e59a20f35d928`: 33 focused / 2302 full PASS (1 skipped), no actual native CLI run in this branch. Fresh native utility follow-up separately preregistered in `AUTOMATION11_C3_CLI_NATIVE_TWO_TURN_PREREG_20261028.md`. All original negative acceptance gates remain unchanged.
