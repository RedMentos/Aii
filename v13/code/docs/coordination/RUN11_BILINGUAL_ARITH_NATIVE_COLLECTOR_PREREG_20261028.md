# Run11 bilingual arithmetic heldout native collector prereg — 2026-10-28

Owner GPT-6, review-only child of #853 at `3c030cd40dd198d80b2792c2d87d60e1e48cafe0`. The parent 16-item corpus is frozen at Git blob `ceda0a5cb506cf09885652b24893cf7d8fdff63b`; parent scorer protocol amended for exact role-specific model hashes before any native heldout execution. This is a **new candidate cohort**, not a retroactive replacement of #848/#849 single-case evidence.

## Experiment scope and fixed choices

Build a serial, bounded `scripts/age0_bilingual_arith_native_collector.py` that uses the real installed V13 Runtime on Linux and the existing pinned model catalog, never a mocked answer. The operator supplies a **fresh isolated Age0 home** already bootstrapped by the existing pinned `v13.bootstrap`; no production user home. The collector verifies `ModelManager.verify(deep=True)`, catalog and prompt Git blobs, exact B1/B2/C3 model hashes, Age0 RECORD_ONLY, stage0, jepa_weight0, and no latent injection before starting.

One turn at a time in the frozen fixture order, with a **new chat session per item** in the same fresh brain home, `answer_language` set to the item's EN/DE label, no memory edits or learning commits. Note: a new session does not prove complete global state isolation; report this limitation. Wait for `Runtime.idle()`, enforce a 120s per-turn limit and bounded cancellation, capture actual persisted FINAL message text and metadata, including `runner.role`, `tool_call`, `tool_shadow`, and source event. Never patch model outputs or fill missing metadata with guessed success. Emit append-only raw per-row JSONL with fsync, plus final strict scorer manifest only after all rows are collected; fail closed if any row missing/non-FINAL/unauthorized. Persist partial failures. No user data is present in the registered public prompts.

This collector is a candidate-native execution tool, not proof that the 16 prompts have actually run. Native execution requires a **separate, exact-source workflow** with exclusive heavy-model ownership and pre/post SHA checks, privacy scan, raw evidence ZIP with SHA256SUMS, no model weights in artifact, and subsequent independent review. Do not start native while another heavy native owner is active. The initial native run should test **candidate prompt only**; baseline pairing requires a separately pinned baseline run with the exact same fixture and a distinct prompt blob. No score improvement claim before both arms exist.

## Falsifiers / software checks

Fail for a missing model, source/catalog/prompt drift, non-RECORD_ONLY or jepa_weight != 0, wrong runner role/hash, no FINAL message, unauthorized tool_call, output-dir collision, cancellation or incomplete 16 rows. A dry/mock test may verify row serialization and gates but **must never be called native proof**. The actual benchmark's validity depends on source-bound native raw, human review of unsupported answers, and unchanged source/seed/model cohorts.

Negative gates remain: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, no Redmi proof, no AGI/whole-system completion.
