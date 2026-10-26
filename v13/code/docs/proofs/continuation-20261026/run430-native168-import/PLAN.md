# Run430 — atomic import of actual Run427 O_s21 168-row safe work

2026-10-26; owner GPT; review-only branch `codex/run430-native168-safe-import-20261026`, stacked on Run429/PR428. Run427 exclusive native O_s21 Actions 40263042202 remains in progress at preparation. No new native/model job.

Run419 importer accepts only 126 rows. Implement a separate 168-row atomic no-model ZIP importer using unchanged Run409 safe publish and Run429 independent verifier: validate observed outer ZIP SHA256, manifest and each file hash, reject duplicate/unsafe/special archive members and symlinks, reconstruct only declared empty directories, run full 168-row source/row/runner validation **before** publishing. On RED, preserve source archive untouched and refuse destination publication. Synthetic adversarial tests check tampered ZIP, missing/unsafe entries and refusal to accept unverified 126-row reports.

Do not invent Run427 artifact IDs/hashes or claim native 168 before actual Actions completion. Once producer GREEN, add a fresh-runner exact-artifact workflow and verify. STEP2/B3/Body-JEPA/jepa_weight/Redmi gates remain negative.
