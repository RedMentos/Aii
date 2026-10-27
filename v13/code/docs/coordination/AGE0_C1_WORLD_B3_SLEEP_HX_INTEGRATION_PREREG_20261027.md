# Age0 C1+World+B3+Sleep A+HX134 integration — prereg (2026-10-27)

Review-only integration from C1+World+B3 all-gates candidate `a46fda283463a3ee47a9e96cab8f2ef16772aa1a` (not main). Independent siblings from the same verified C1+World+B3 seed ancestor `1ab88aa30947e2f3da9905b1d3055f04b98a8bed`:

- Sleep A exact-memory-ID retention review `assistant/v13-sleep-a-exact-recall-identity-review-20261027`, prereg `d9ee59ef7d189334533f58a9be63229466fa345f`, test-only RED `19c048e1f8fc585082acafa911d41ef0e24123ed`, source fix `9baa1d10db813f45d0a7082aa353e0da2d8f4676`.
- Claude HX1/HX3/HX4 SHADOW integration `assistant/v13-hx134-c1-world-b3-integration-20261027`, prereg `ed0eb935135cf2824a236cb63f5752e5d27687a4`, test-only RED `cf6b7adaac7416743a488e30564602630c52fb66`, exact Claude source merge `34c9d0dc6d6945d717f4fa0156bbcc64e8245e05`.

## Scope and merge contract

Do not merge until all three full software suites pass and source blobs are verified. Changes are disjoint: B3 `b3bridge.py`/`b3degrade.py`, C1 `executive.py`, Sleep `sleep.py`, HX `agi/__init__.py`/`agi/self_improve.py` plus new modules. Merge only changed code/test/workflow/coordination paths; preserve original hashes and negative gates. Do not transplant stale ROADMAP or HANDOFF from Claude's old branch. Use explicit two-parent commits without force-push, then run combined focused and full software suite with raw exits and privacy scan.

## Acceptance and limits

Combined C1 provenance, B3 seven-arm seed/report/promotion, Sleep A source-bound retention, and HX allow-list/approval/rollback/blind selector tests must pass. HX live consumers remain 0, no self-modification authority. No native model/Redmi, no Body-JEPA/STEP2/B3 utility promotion, `jepa_weight=0`, Age0 and whole-system incomplete. Preserve failed attempts, hash ZIPs, private backup, draft PR for independent review. No auto-merge.
