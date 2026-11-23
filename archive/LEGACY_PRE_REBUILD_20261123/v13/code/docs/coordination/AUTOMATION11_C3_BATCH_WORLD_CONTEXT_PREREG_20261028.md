# Prereg: merge C3 bounded F1/F5 scoped-batch verification with World-JEPA and Context OS (2026-10-28)

Owner: independent C3 source-consumer integration lane `assistant/v13-run11-c3-batch-world-context-20261028`. Parent is independently audited three-organ software integration #901 head `1743e0f723e3dc16fbc610b254cfbfa03f398a90` (76 focused / 2326 full software OK, raw ZIP SHA256 `e6c36ce60e4c2e78319c6c185d5e9d82830e3fac398decf78434ce301bd8720c`). Donor #897 exact head `ea906529bdbbad8b40e73b0c7ac98c5e0ecb9d3e`, independently audited 53 focused / 2322 full software OK on its own branch.

## Bound change
Import all five donor paths byte-identically in a real two-parent merge: C3 `source_consumer.py` `4b73842be25e784f70ade4f6c4ced3fe2dcb9eab`, `test_source_consumer_recall_integration.py` `c3689b73043d9655cc71e54cee2c87421f3666fc`, workflow and donor evidence/prereg. The donor batches at most 256 scoped active corrections through `Memory._verified_rows(scoped)` once, requires unique exact IDs, refuses unreadable/invalid rows, retains same-project hidden conflict veto. Do not change active source/seed/model/correctness policy or unrelated C3/ContextOS/WorldJEPA code.

## Evidence and falsification
- Integration focused tests must include active hidden conflicting correction, corrupted active correction, revoked source, cross-session source, post-generation source revocation, sealed renderer and original C3 CLI. Context OS long/multiline exact quote and World-JEPA invalid transition controls must remain GREEN. Full software suite, compile, privacy/diff, pinned blob checks and closed raw artifact.
- **Performance improvement is a hypothesis**; donor only establishes one batch invocation in software, not measured wall-time speedup, native token speedup or Redmi benefit. Measure separately if useful.
- Native C3 replay #903 currently runs on the **pre-batch** source. Its results must not certify this changed C3 source. A new source-pinned native proof will be required if this candidate is adopted.
- Keep frozen Runtime `68e7ed1352800174972558f1e0b0683a42c8689a`, model catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, C3 GGUF/revision/seed and all original cohorts unchanged. Age0 RECORD_ONLY/SHADOW, `jepa_weight=0`.
- No production merge or original Stage11/STEP2/B3/Body-JEPA/LP3/Age/Redmi/full-system gate promotion.

Next: source-pinned focused/full integration run, independent raw audit, private Library backup and verified GitHub checkpoint; then assess measured utility or next canonical package.
