# GPT independent cross-review of Claude PR641 — exact route labels (2026-10-27)

Review base: Claude PR641 `claude/project-thread-h02m13` at `bc0703f4fbfb794b23ffc49ac8a7cb6074903bfa`. **Isolated review child**, not a merge into Claude's branch or Codex's Run643 chain. Only `learning_worker.py`, one test and scoped CI/evidence changed. Original Z6i/Z6i2 datasets and registered model/seed hashes remain untouched.

## Confirmed defect and repair
PR641 `learning_worker.train` silently coerced human `labels` and `scaffold_labels` through `np.asarray(...,dtype=int)`. Values `True`, `0.9` and `'2'` became legal class IDs. This breaks the explicit-human-label integrity rule, especially when evaluating or training a learned route head. Repair uses the same type-exact `exact_route_labels` logic already present in the Codex integration chain: JSON lists of Python integers 0..3 only, exact scaffold length, no bool/float/string conversion. No change to word-channel features, optimizer, weights, relative gate or rule handover.

## Preserved original failures
- **CI harness RED** Actions **40439693707** at `33beb2091798542080f9a7718a8d6ab91baf3019`: copied workflow referenced nonexistent `test_review641_curiosity_receipt.py`; dependency/test step never ran. Diagnosed prospectively in `AMENDMENT1.md`, then fixed paths only. Raw artifact SHA256 **d5423b997a948dd502b5fe6bd799e1361fa41d235cb542725bab99b60b6a67ad** (artifact 12705413024); no learning claim from this harness error.
- **Actual original behavior RED** Actions **40439829915** at `d470ae79da8ac2cf42f2e6c1077975ab06d8b52e`: **15 tests, 4 FAIL** on bool/float/string human label and bool scaffold; positive valid integer test and existing route-word/worker regressions passed. Privacy CLEAN. Original raw artifact **12704934479**, SHA256 **75134a1969c31f83301cee9be8f21d50508eda469c76ba99b725e46b4457aa40**.

## First GREEN
- Actions **40439896899** at exact source `c0b3fbd61d03078f41862f435796a46cff142525`: **15/15 PASS**, privacy CLEAN. Raw artifact **12705327640**, SHA256 **ad58d23e28dd19608a939b7ee5edd4d7231b4d4e5a01c461218363d91b795382**.
- RED and GREEN originals downloaded, ZIP CRC and source HEAD/exit codes checked; private Library `/V13-Checkpoints/2026-10-27/Review-PR641-Labels/`, byte-identical rematerialization of actual behavior RED and GREEN.
- Whole-suite workflow **40439740244** on pre-repair head and **40439896933** on repair head were running at initial report; **no full-suite PASS claimed** until their results and raw logs are verified.

## Limits and next
Review only, not merged. Existing `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, Body-JEPA unavailable, `jepa_weight=0`, Redmi unmeasured, V13 incomplete. This test is Linux software with synthetic embeddings, not native learned utility. Next: inspect full-suite workflows, retain raw; ask Claude to integrate reviewed fix after their own review, or cherry-pick safely into an explicit integration branch. Another independent route handover idempotence counterexample may be worth testing: repeated `observe` on the same event could count as multiple distinct agreements.
