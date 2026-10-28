# Prereg: fresh disjoint C3 source-use on batched F1/F5 + ContextOS + atomic World-JEPA (2026-10-28)

Owner: isolated native validation lane `assistant/v13-run11-c3-batch-world-atomic-native-fresh-20261028`. Parent #905 exact source `4e24234b5c26df7438c5f9af1b23a38e9b2263e3`, combined software run `40674664303` **PENDING at prereg**. Do not start heavy native until source-pinned combined software is independently audited GREEN and the existing native concurrency group is idle.

## Frozen NEW disjoint test cohort (no post-hoc substitutions)
Two independent synthetic named project-budget facts, separate sessions:
1. EN: `Project Ilyora budget = 517 Euro`; query `What is the budget for Project Ilyora?`.
2. DE: `Project Keldara budget = 846 Euro`; query `Projekt Keldara: Wie hoch ist das Budget?`.

Fixture rows in `(project,amount,language,topic,value,query)` format with JSON `sort_keys=True,separators=(',',':'),ensure_ascii=False` yield **SHA256 `9dfd73282974634cbfe826d3b9fa45f7d0cdc76e5eb6a8525603deda55f097b2`**. This is a **new cohort**; do not alter old Veloran/Mirava, Averdin/Nerissa, registered STEP2 or other seed/model cohorts. Seed 13, frozen C3 revision `657e078c94084481950a2d555a941481f715536b`, GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, frozen catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, Runtime `68e7ed1352800174972558f1e0b0683a42c8689a`.

## Locked test
- Reuse existing proven isolated native collector semantics without modifying old collector. Copy into a NEW script with only new `PROJECTS` and `FIXTURE_SHA256`; pin new script Git blob and all unchanged source/runner hashes. Test each positive with preflight READY, actual one native FINAL, exact amount, model revision, reaped worker. Run four negative cases for each project (no source, wrong project, conflicting source, malicious source) and require CLARIFY with zero native calls. Require 2/2 positive and 8/8 negative, exactly two native calls, model hash unchanged, no integrity errors. No adaptive retry or changing fixtures after a failure.
- Source-pinned workflow: exact blobs, bootstrap deep hashes, focused software, native raw report, compile, privacy/diff, closed SHA256 manifest. Independently audit ZIP, private Library backup and readback.
- If any native output is RED, preserve raw and report failure; do not silently tune prompt, cohort, seed or source and re-run. A separate prereg is required for any new attempt.
- Native Linux C3 operator CLI only, not normal Runtime._turn, not measured Redmi, not actual World-JEPA learning. Age0 RECORD_ONLY/SHADOW, `jepa_weight=0`. No Stage11/STEP2/B3/Body-JEPA/LP3/Age/full-system gate promotion.

Next: wait #905 software audit; then create new collector/workflow from frozen source, run serial native, independently audit and checkpoint. Continue functional blueprint gaps after proof.
