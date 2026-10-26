# Run427 — one pinned Linux-native O_s21, serialized behind active S owner

2026-10-26; owner GPT; review-only branch `codex/run427-native-o21-serialized-20261026`, stacked on Run426/PR425. Before scheduling, exclusive native Run418 Actions 40260397013 was still IN_PROGRESS in step "Execute exactly one pinned native S_s20 arm and safe no-model export". **Never run heavy native jobs in parallel.** New PR workflow uses the exact existing native concurrency group `v13-native-c3-run131-serialized`, `cancel-in-progress: false`, so its native work queues until current owner releases. No force push/merge.

## Bound prerequisites
Run425 actual independent no-model 126-row import verified (Actions 40262481461), from Run418 producer Actions 40260347495:
- small raw artifact 12625030366, SHA256 `54a6b12638dfdc0e9f71f362d3357dd70adfe0ba2441d26c4c3eba3e37bb364b`;
- safe no-model work artifact 12624815819, SHA256 `20ce321d29f04089a087421e16ddd5d854c103d36b7c958e4b0e11815f45cac4`.
- exact Run394/397 frozen source and model catalog blob hashes, exact pinned runner b10964, exact pinned public model file hashes.

## Work
Use unchanged Run419 importer to verify actual 126-row source, then unchanged Run421 `stage4 --execute` with `max_new_arms=1` to add exactly `O_s21` (42 native rows, total 168). No O21 attempt if any hash/source/owner prerequisite fails. Keep all raw failures and safe export even on partial interruption; upload only small raw plus no-model safe work ZIP, never model files. Exact native proof is Linux, not Redmi. STEP2 remains `UTILITY_FAIL` even on 168 structurally valid rows.

## After
If actual GREEN, independently verify 168-row export in a separate review package before P_s21. If RED, retain raw and do not silently retry or promote. Continue other canonical packages while queued.
