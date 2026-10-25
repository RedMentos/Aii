# Run279 — fast episodic route F5 authority (2026-10-25)

## Dependency and owner
- Base: verified Run278 PR278 checkpoint `dea929160d8fed7a9008219e3a1026668ae099f5`. PR270→271→272→273→274→275→276→277→278→279 is a dependent review chain; never merge this PR directly into old main.
- Disjoint owner: `v13/code/v13/episodic_route.py`, new Run279 test, CPU-only CI and this proof directory. No edits to Run278 or PR277-owned files.
- Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, original BUILD_STATE `fdf0827d7c4af5cdb85b69cbe651ed52784a07b5`: unchanged.

## RED — actual Runtime/SQLite, no native model
- Test commit `20c58d4df5a11ab4a9a77ce70599c476d7bf5730`; CI commit `791db14b0ca25f8149e86ed92be5753bc8e4fe5e`.
- Exact-head GitHub run `40191837192`: **30 tests; 9 failures**, 21 pass. Valid record/learn control passed.
- Missing feedback, duplicate feedback, wrong feedback kind/value/permission/event, nonhuman source kind, forged HumanDecision producer and independent-route invalidation all exposed old fast route. Original route-specific MemoryRecord/HumanDecision checks alone were insufficient.
- RED raw artifact `12597988141`, ZIP SHA256 `6f856002da0cd3f28716d4a9d3a3555159f3293099c3d929bb2b5ef871c4c6c0`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40191837192/artifacts/12597988141

## GREEN and review
- Production commit `711bfb11205dafb039df427b44854db6a1d4b1ef`: batch-filter route candidates through existing F1/F5 `Memory._verified_rows`, then retain original route-specific `_source_bound` checks. Active and shadow fast routes both fail closed after revocation. No new learning rights, no model changes.
- Exact-head GitHub run `40191893333`: **30/30 PASS**, compileall PASS, official privacy scan CLEAN. Additional Run107 route provenance and Run112 integration workflows PASS at this head. Source-only Linux/SQLite evidence.
- GREEN raw artifact `12597938414`, ZIP SHA256 `606fe4b04b2270e42505527b9a52fdaf0d690fda724841b864490f0adc2422d9`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40191893333/artifacts/12597938414
- Remote blob readback: production `c4ca21f413d7108e00b92ee5578a809e35bac699`, tests `a29b60c9775a72dd866e146a86f438b1d90c281e`, workflow `1b3d97efab51c3d406b2006ac60e0b4c7747662c`.
- No separate independent agent ran; adversarial RED/GREEN and neighboring Run107/112/270/274/278 cross-tests provide software cross-check, not native/full-suite proof.

## Other current-chain evidence and blockers
- PR277 exact-head CI `40189028071` remains FAIL due offline dependency installation; separate review comment `6397422423` retained.
- PR269 full registered actual-weight Linux acceptance `40186761125` completed **20/20 stages attempted**, **11 PASS / 9 FAIL**, final `IMPLEMENTED_PATHS_PARTIAL`, exit 2. Native weights/runner were downloaded and hash-verified; this is a real negative native result, not a missing-cache inference. Raw artifact `12597232047` SHA256 `eac321b4f8119f0ce10cbd65c050c87e56f11b94ec8d56322f450014f13054d0`. No Redmi.
- Original gates remain STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE`.

## Exact next package
- Do not rerun heavy native acceptance concurrently with any active owner.
- Read-only triage of PR269 closed stage JSON and failures, prioritizing `jef-modes`, `executive`, `step12` and `cancel-restart`; identify reproducible software-level defects without changing registered native cohort or gates. Use a separate branch/file owner for any fix, RED-first tests and independent review. Current local container has no full Git checkout due GitHub DNS failure; GitHub connector and exact-head CI are available.
