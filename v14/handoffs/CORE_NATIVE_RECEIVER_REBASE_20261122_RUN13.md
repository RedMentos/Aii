# Core & Harness — native receiver rebase on current Boss (2026-11-22)

## Ownership and exact Git state

- Owner: Core & Harness
- Working branch: `core/v14-native-receiver-currentboss-20261122-run13`
- PR: [#2309](https://github.com/RedMentos/Aii/pull/2309), DRAFT / NOT_RELEASED
- Code commit: `74c43a98fa5ad99138714cc0d6e54bd6bb3d2c88`
- Exact integration base: `boss/v14-recall-store-pin-rebind-20261122` at `0441ab8b229dd17343c03d9350c6848115220416`
- The base includes the Age-rights integration from PR #2307. No release branch or installed phone runtime was changed.
- Old PR #2300 remains untouched as historical evidence; its branch is not used as the new base.

## Reproduced defect and repair

Old #2300 head `767a8006760498c63f7a1f81bd9e4c5e003fd57c` had 7/18 check-runs passing and 11 failing. The first direct failure was `integrated builder hash mismatch`. Readback showed stale SHA-256 pins at every layer, including raw Core source files and the four native receiver files.

The rebased commit recalculates all exact source pins and reconnects the staged composition chain:

`native source files → native overlay → recovery composer → integrated stage builder → runtime deployer`

Exact readback:
- Native overlay SHA-256: `6b266a28c808460634661f5d704e685cf127c118564aab4c8c5f2f1c1741e6cd`
- Recovery composer SHA-256: `6032cc589baf81da23b7cee7b67f1e6716f86f1017f73e21ae1b691a24bc8379`
- Stage builder SHA-256: `3cd25d36767d9d7dc7a6f4bd5f26e3caf43103ca9af8dd630b5033f070cbbe2c`
- Runtime deployer `STAGER_SHA256` readback matches the stage builder SHA above.
- Stage builder `BUILDER_SHA` readback matches the recovery composer SHA above.
- Recovery wrapper `NATIVE_RECEIVER_SHA256` readback matches the overlay SHA above.

The six raw-source pins and four native-file pins are recomputed from the exact current Boss/PR file bytes; the staged test is the executable check that applies the full chain.

## Function and safety boundary

- The explicit `:callosum native-probe <sender> <receiver> --last-source --confirm` path remains a one-shot diagnostic probe.
- It consumes sender activation rows through the pinned llama.cpp `llama_batch.embd → llama_decode` path and stores a source-bound diagnostic receipt.
- `production_route=false`, `semantic_use_proven=false`, `training_authority=0`, `native_receiver_authority=0`.
- No trained cross-model projector, semantic utility claim, production B3 routing, KV-cache injection, model download/swap, weight update, permission change or user-data mutation.
- The native binary is not yet packaged by the normal updater. A separate local user-confirmed probe would be required after packaging.

## Tests and environments at handoff

- Exact-head CI for `74c43a98fa5ad99138714cc0d6e54bd6bb3d2c88` was started; the following were queued/in progress at readback:
  - V14 native latent receiver staged runtime — run `44987937931` QUEUED
  - V13 staged context and integrated regression — `44987937859` IN_PROGRESS
  - V13 private owner-read Termux bootstrap — `44987937850` IN_PROGRESS
  - V14 Core same-turn B1/B2/C4/C3 and source-read revocation — `44987937895` IN_PROGRESS
  - V13 Lab Age control state and WebView truth — `44987937886` IN_PROGRESS
  - V13 runtime deployment integrity — `44987937975` IN_PROGRESS
  - V13 Laboratory Age two-checkout updater migration — `44987937950` IN_PROGRESS
- The old #2300 head had PASS for the pinned Linux llama.cpp build and Android ARM64 cross-compile, but those are not evidence for this rebased head. Re-run on #2309.
- LOCAL_LINUX full repository tests: BLOCKED — no local Aii checkout and GitHub DNS unavailable in the execution container.
- Android ARM64 cross-compile: NOT_YET_VERIFIED on this head.
- Native GGUF receiver execution: NOT_RUN.
- Redmi/Termux: REDMI_UNVERIFIED. No private owner receipt, device command, update request or phone mutation was attempted.

## Integration coordination

- This PR modifies the shared recovery/stage/deployer pin chain. JEPA #2305 and Perception #2304 also modify that chain on older bases. Integrate serially and rebind every affected pin after each overlay; do not replace this chain with a stale stage file.
- Shared `V14_WORK_BOARD.json` and `V14_USER_NEXT_ACTION.md` are intentionally not edited in this Core branch because the active #2304/#2305 branches also modify those shared files. Boss should fold this exact handoff into the shared board and next-action file during coordinated integration.
- No release or deployment claim.

## Next executable step

1. Read all exact-head CI for #2309 and repair any real failures.
2. Add a same-model token-prefill versus embedding-input parity control to the native receiver, then measure actual receiver utility against zero/shuffle and SOURCE_EXACT/NO_MESSAGE baselines.
3. Only after a real compatible model and consented device execution exist, capture native rows/dimensions/tokens/latency/RSS and receiver output effect. Keep B3 production OFF until a trained cross-family adapter has held-out utility, retention, restart and rollback evidence.
