# Run416 — fail-closed O/P receipt preflight before Run415 S_s20

2026-10-26 · owner GPT · isolated review branch `codex/run416-stage3-native-preflight-20261026`, stacked on Run415/PR411 at `dfadb06fa84dcb4de45ca62e00027b8eb065706a`. Not merged into main. Run413 original native P_s20 owner Actions 40258333913 was still IN_PROGRESS when this package began. No competing native job launched.

## Defect / impact

Run415's source-only restore verifies Run413's safe export manifest and high-level 84-row progress, but the optional native path previously entered `resume.run(... max_new_arms=1)` without validating both O_s20/P_s20 per-attempt receipts. Run397 intentionally treats an invalid previous attempt as failed and proceeds to the next missing arm. Consequently a corrupt or source-incompatible O/P attempt could consume the exclusive next native slot on O or P rather than intended S, even though the outer postcondition would ultimately report RED. A forged progress attempt path could also cause an unneeded out-of-tree read if trusted in a new preflight.

## Scoped change

Before native execution only, check the exact frozen Run394 preregistration, progress gate, O/P keys, no preserved failures, bounded attempt paths, actual O/P receipts through unchanged Run397 `validate_completed`, current pinned runner SHA, and 42 rows per arm with exact stored receipt equality. On any mismatch: no `resume.run` call, preserve original work/failed attempts, export the restored no-model work through the existing Run409 fail-closed exporter, return RED. Successful source-only restore remains available without models. New adversarial tests cover altered model identity, 41-row receipts, resealed but changed frozen manifest and traversal, as well as inherited synthetic success/failure.

## Evidence and claim limits

Only source-only/synthetic tests are eligible in this package. Native P_s20 and S_s20, 126-row utility, Redmi, Body-JEPA and whole V13 remain NOT PROVEN. No model/seed/cohort hashes or frozen Run397 runner modified. `canonical_gate_pass=false`, `step2_exit=UTILITY_FAIL`, `jepa_weight=0`. GitHub Actions `run416-native-preflight-source.yml` captures exact head, SHA256, test output, privacy output and hashed small raw artifact. CI results must be recorded separately after actual completion, never inferred from code.

## Exact next actions

1. Check Run416 exact-head source-only CI and privacy scan; preserve any RED output and fix only confirmed defects.
2. Independently review the new preflight against unchanged Run397 receipt semantics.
3. Await actual Run413 P_s20 GREEN, independently verify the no-model artifact and exclusive native owner, then execute Run415's opt-in S_s20 on the pinned Linux-native host; never treat source-only tests as native evidence.
4. Continue an independent canonical work package while native work is blocked.
