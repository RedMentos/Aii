# Run93 prereg — real source-bound C3 answer from persisted Age0 F1/F5 memory (2026-10-29)

Owner: GPT-6 scheduled continuation. **Pre-register before runner/workflow implementation and before the native experiment.** Review-only child of Run92 #999 exact `58eb54a05532a5b9d25bd9713faf3bec1d55baff`, itself a review-only child of Run83 #990. Do not merge main, modify active cohorts, or infer production integration.

## Question / actual V13 utility

Does the **current pinned** C3 350M (not the historical 230M) answer one user-provided exact project budget after it is committed in a real Age0 Store/Memory F1/F5 SourceRef, with native decoding and verified release, while missing/wrong-project requests produce no native calls? This is an isolated **existing-home operator candidate** using the existing `scripts/ask_verified_budget.py`, not a change to frozen Runtime._turn, and not a STEP2 or general C3 quality claim.

## Frozen inputs and cohorts

- Platform: GitHub-hosted Ubuntu 24.04 Linux x86_64, isolated fresh venv and home. No Redmi claims.
- C3: `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, `LFM2.5-350M-QAD-Q4_0.gguf`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, 219312832 bytes, LFM Open License 1.0.
- Runner: llama.cpp `b10964`, same pinned catalog and install-native path as Run92; Needle-3 support installed solely because `install_native` requires it, not evaluated as C2.
- Frozen source Git blobs: `scripts/ask_verified_budget.py` `75ca7f3f197665f665d9582b7f5c2efb1f598235`; `v13/source_consumer.py` `4b73842be25e784f70ade4f6c4ced3fe2dcb9eab`; `v13/memory.py` `53dc948d0d360f94743ad996eb83ea0e85c2dd0b`; `v13/operator.py` `7bf3a992af1db87f6ee2432c2486dbbced0f2bd4`; `v13/runtime.py` `68e7ed1352800174972558f1e0b0683a42c8689a`; `v13/models.py` `bd035cf8029850cce00b179edf533e53bf24358a`; `v13/bootstrap.py` `dc23e192bcd01589475692666ebb6568c80d078b`; `specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`; `tests/test_ask_verified_budget.py` `efb239a116e463bea8e47a43ea841c2b2a599af4`; canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Do not edit them for this cohort.
- Source: a newly created real `Runtime` session, user-recorded correction `Project Elyra budget = 615 Euro`; no other project-budget corrections. Query: `What is the budget for Project Elyra?`. Control: `What is the budget for Project Dovan?`. Native seed **13**, max **64** output tokens, deadline **90 s**.
- No private/user data. These authored synthetic names/values are fixed public fixtures; no GGUF or executable binaries in evidence.

## Precommitted sequence and outcomes

1. Install current C3 + Needle, pinned native runtime. Deep SHA verify. Close installer. No body model install.
2. Start real Age0 `Runtime` with sleep disabled, record one `Memory.feedback` fact via real `Store.event`; call operator `:verified` (must be READY, zero native calls). Close Runtime; reopen with `BudgetContext` from same home.
3. Negative before native: Dovan and out-of-scope/no-source requests must be `CLARIFY` or `NOT_APPLICABLE` with `native_calls=0`, no `answer`. Positive `query(native=False)` must be READY with exact persisted SourceRef.
4. Positive `query(native=True,timeout_s=90,max_tokens=64)`: **one actual native call**, process reaped; report status FINAL and exact 615 Euro source only = narrow `SOURCE_C3_ANSWER_PASS`. Any model refusal, bad answer, timeout, missing model, unverified release, or source mismatch is **RED** for this exact narrow claim, not permission to alter source/seed/prompt or hide output. Preserve original RED evidence, independently analyze failure.
5. Reopen the persisted home; `:verified` remains READY without a model. Forget the fact via real human operator `:forget <id> --confirm`; after forget `:verified` must be CLARIFY. Native must not be called on revoked source.
6. Run existing `tests.test_ask_verified_budget`, `tests.test_source_consumer_recall_integration`, `tests.test_run83_age0_backup_restore_e2e`, `tests.test_verified_operator_preflight` plus full suite. Hash-close raw output, status, source and privacy/diff. Native result never substitutes for full-suite or Redmi evidence.

## Explicit negative gates and stopping rule

Age0 RECORD_ONLY, `latents_enabled=false`, `jepa_weight=0`, no auto-approval/learning/tool side effects. This experiment is **one authored synthetic factual query with real Linux native C3**. No B1/B2 learning, JEPA, B3 receiver, STEP2 utility, Body-JEPA, LP3, general semantic reliability, Redmi, Age promotion, or whole-system completion. If native RED, preserve it and pursue an independent package; do not change frozen source/fixtures or repeat the registered cohort.