# Run101 prereg — two distinct persisted F1/F5 project sources -> current pinned C3 Linux-native (2026-10-29)

Owner: scheduled GPT-6 continuation; isolated review-only child of **independently raw-audited Run93 GREEN** `896a4087acc0dcf7427e6860b5a0bc04cd7057cb` (#1000, Actions 40793940915, original ZIP SHA256 `302f89a9ae849e199b54abfa2f7dd9f4fc76c273751a2df823d6a8abffce58f7`, 20/20 inner hashes, 29 focused/2653 full OK). This preregistration must be committed before script/workflow and before native runs. Not a main merge or gate promotion.

## Distinct hypothesis and exact inputs

Run93 proved only one synthetic Elyra budget. Run101 tests whether the **same frozen source-guard and current C3** handle **two different positive projects coexisting in one real persisted Age0 session**, without leaking the other project's value, and refuse missing/out-of-scope/conflicting sources. This is new generalization evidence, not a repeat of the Run93 fixture. Frozen scripts `scripts/ask_verified_budget.py` blob `75ca7f3f197665f665d9582b7f5c2efb1f598235`, `v13/source_consumer.py` blob `4b73842be25e784f70ade4f6c4ced3fe2dcb9eab`, `v13/memory.py` `53dc948d0d360f94743ad996eb83ea0e85c2dd0b`, `v13/runtime.py` `68e7ed1352800174972558f1e0b0683a42c8689a`, `v13/operator.py` `7bf3a992af1db87f6ee2432c2486dbbced0f2bd4`, `specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, canonical handoff `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; **no edits** to these.

Model: current `LiquidAI/LFM2.5-350M-GGUF` at revision `657e078c94084481950a2d555a941481f715536b`, GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, pinned llama.cpp b10964; Needle support solely for native installer. Ubuntu 24.04 x86_64, isolated fresh home/venv. Two public synthetic facts created with real Runtime/Store/Memory feedback, same session:
- `Project Dovan budget` = `731 Euro`; query `What is the budget for Project Dovan?`
- `Project Mira budget` = `942 Euro`; query `What is the budget for Project Mira?`

Control queries: `What is the budget for Project Elyra?` (no source -> CLARIFY), `Who leads Project Dovan?` (out of scope -> NOT_APPLICABLE). Negative after native: conflicting second verified `Project Dovan budget` = `809 Euro` -> CLARIFY without native, never expose either number. Post-forget: revoke both original and conflicting Dovan facts -> CLARIFY; Mira must remain source-bound READY. No user/private data.

## Frozen procedure and decision

1. Install only pinned C3+Needle+runner via existing Run93 installer, deep SHA verification, no B bodies. Fresh Linux temp home, RECORD_ONLY, latents false, JEPA weight zero.
2. Record both sources in one real Runtime session; `:verified` each READY and distinct SourceRef. Close/reopen. Negative controls and model-free READY must call native zero times.
3. For Dovan and Mira **in that order**, call existing `scripts.ask_verified_budget.query(native=True, timeout_s=90, max_tokens=64)`, **seed13 fixed by frozen query**. Each must return `FINAL`, `native_calls=1`, `model_called=true`, `process_reaped=true`, same pinned revision, exact matching project+Euro source only. Any failure is **Run101 TWO_PROJECT_RED**; preserve all actual responses and original raw artifact. No prompt/source/seed/threshold retuning on this cohort.
4. Reopen Runtime; introduce verified conflicting Dovan 809 Euro and assert no C3 call/CLARIFY; forget both Dovan corrections and assert still CLARIFY. Mira remains READY. Include full focused/full unit suite and source/privacy/diff checks.
5. SHA-close original raw ZIP (HEAD, source blobs, install, native, tests, exits, report), independently audit CRC/inner SHA256SUMS. Private persistent backup if available.

PASS requires **both** positive native answers and **all** negative/persistence/teardown controls. Report per-case raw statuses and outputs even if RED. This tests only two authored synthetic source-backed Linux-native C3 turns, **not** general factual QA, Android/Redmi, body complementarity/STEP2, B3, JEPA, LP3, learned weight utility or complete V13. No age/tool/learning authority changes. Next independent package after result: investigate failure without changing registered cohort, or move to another organ if blocked.
