# Run397 — restart-safe execution of the already frozen Run394 native STEP2 cohort

2026-10-26. Owner: GPT scheduled continuation. Independent source-only package while Run395 serial native job is active; **do not start competing native inference**. Files owned: `scripts/run397_step2_resume.py`, `tests/test_run397_step2_resume.py`, dedicated workflow/proof folder. Base Run396 checkpoint `9c2e10426b970d25cdd7cde9c666a6e4b68fbf23`, stacked review, not main.

**Observed gap:** Run394 saves per-arm raw and `RUN394_PROGRESS.json`, but its `z2.sibling_home` rejects an existing arm home; after SIGTERM/timeout in a partially completed arm, naive rerun in the same work directory fails. The planned 378-row full cohort needs bounded, append-only retries, not deletion or unverified reuse.

**Implementation target:** New opt-in orchestrator reuses Run394 frozen fixtures/arms/seeds, registered public installed artifacts, and unchanged native harness. It creates a unique attempt directory per arm/seed, never deletes or overwrites an attempt, reuses only completed arms after checking row hashes, tool replay preregistration, source/model integrity and zero wrong committed actions. Partial/failed attempts remain closed evidence; on retry, create another isolated attempt directory. Persist a root append-only progress journal with attempt paths, hashes, failure reasons, current owner and next action. Fail closed on manifest changes and concurrent owner lock. No auto-resume after permission/age changes, no silent model substitutions.

**Tests:** source-only synthetic fixtures for partial attempt, completed attempt reuse, tampered row, hash drift, concurrent lock and no overwrite. Independent GitHub Actions exact-head CI, raw SHA and privacy. No new native execution while Run395 is active.

**Acceptance:** source tests and privacy pass; actual restart recovery remains UNPROVEN until a deliberately interrupted Linux-native run is completed and independently verified. No STEP2/B3/Body-JEPA/jepa_weight/Age/Redmi/whole V13 promotion. Run389 full-suite RED retained.
