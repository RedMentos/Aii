# Prereg: merge source-backed C3 CLI postflight + live renderer + scoped conflict veto (2026-10-28)

Owner: ChatGPT continuation, review-only new branch `assistant/v13-c3-cli-render-integrated-20261028`. **Before integration source edits**, exact parent heads: CLI native review #895 `64e10d6b90a1a2fbdf593baa2e1f5e2aa6656ed8`; sealed live renderer and active scoped integrity veto review #894 `b8da4b05b7a11a6a963bdb3462cbade85b86378d`. Neither parent is production-integrated.

## Read-only tree comparison before merge
Both recursive trees complete (not truncated). Relative to #895, #894 has 13 unique blobs and exactly two changed paths: `v13/code/v13/source_consumer.py` and `v13/code/tests/test_source_consumer_recall_integration.py`. No other overlapping blob differs. Plan is a **true two-parent merge** with all 13 unique #894 blobs added and those two paths taken from #894, preserving all #895 CLI/native files, provenance, model/catalog, frozen runtime and historical evidence. No force-push or rewrite of either owner branch. Explicit post-merge tree audit must show union, correct parent SHAs and unchanged original blobs.

## Test protocol
- Add one integration counterexample to existing CLI tests: a valid same-project correction plus an active unreadable competing correction must refuse preflight and never acquire native C3; an unmodified single-source correction still preflights READY and a fake runner's postflight still yields FINAL.
- New branch-specific source-pinned Actions focused suite covering CLI, no-worker, admission, data-boundary, recall, render seal and live revalidation; full software suite, compile, privacy/diff and SHA256 raw artifact. No software PASS until exact-source logs independently audited.
- If software GREEN, separately preregister a fresh disjoint native C3 cohort on the **merged source**, with frozen catalog revision/seed and no adaptive retries. Never reuse Calvorn/Zemira or Averdin/Nerissa as a new heldout.
- Preserve original Stage11/STEP2/B3/Body-JEPA/LP3/Age/Redmi gates. This remains an isolated operator CLI, not normal Runtime._turn integration; no atomic guarantee after final source check. No Drive anyone-writable destination.

Next: create merge tree, commit with both parents, verify remote ancestry/tree, then test.