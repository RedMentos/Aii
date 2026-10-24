# Run96 result / BUILD_STATE delta — fresh corrections wake replay

2026-10-24. PR #128, branch `codex/sleep-wake-index-run96-20261024`, parent Run95 PR #127 checkpoint `8a43aed3bb6782bbea4fe3b3dd7d584e6aceb11a`. Run94 World Model owner not touched.

**RED:** preregistered tests-only commit `8bc3639fab92c012ec87af2420ea36b643958288`, Actions run 40137033208/job 121000621192: 1 new real Runtime/SQLite test FAIL (`REPLAY_DUE` missing after new correction; only `IDLE` posted), three new controls PASS and 46 inherited Sleep/Age controls PASS. Full original log retained.

**Fix:** `SleepRuntime.tick` now synchronizes the durable `replay` table with the derived bounded schedule only after the configured wake idle threshold and outside CRITICAL/PRESSURE, before deciding whether a wake replay is due. It persists changed schedule state with optimistic CAS. If CAS loses, it reloads the winner and never posts from unsaved state. Disabled Sleep and busy foreground do not sync or schedule. No new autonomous permission or learning authority.

**Independent cross-review:** new real scheduler test verifies PENDING wake event and replay index survive Runtime close/reopen; default learning mode remains RECORD_ONLY. Separate local Linux reconstruction: downloaded verified Run93 Phone source ZIP SHA256 `3e4915ceb3b970259aaeeccb01bafed97d3ef042db2e98426b7d6b82e9988ae3`, applied exact Run95+96 source patch and confirmed git blob SHA `b87015134266cbaab14023fdf028df6e855fdb2c` equals remote; **401/401** selected software regressions PASS (15.518s), **14/14** extracted phone operator/CLI tests PASS (26.181s). This is reconstructed source with exact patched sleep.py, not a complete native or Redmi proof.

**GREEN:** Actions run 40137245924/job 121001263197 SUCCESS: **51/51** Runtime/SQLite/Sleep/Age tests PASS, compileall PASS, official public privacy scan CLEAN. Broad focused Actions run 40137245931 was in progress at initial checkpoint (selected software tests and privacy/ZIP manifest audit already PASS; extracted phone tests pending), no final success claim until verified.

**Current host prerequisites rechecked 2026-10-24:** cgroup2 mount read-only; memory.max 4294967296; `transformers` and `llama_cpp` absent, `numpy`, `torch`, `huggingface_hub` present; no .gguf/.safetensors under /mnt/data. Native LP3 cohort, cgroup atomic containment, global owner, Redmi and full model utility NOT RUN/UNVERIFIED. Missing models are not a reason to stop other packages.

**All original gates:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a FAIL, Z8 FAIL, full V13 INCOMPLETE. Source/blueprint/registered cohorts/age defaults untouched. No Drive retry.

**Open questions:** Sleep schedule read/sync at every eligible idle tick may impose battery/SQLite overhead on Redmi; benchmark there before claiming mobile efficiency. Old protected replay items outside MAX_ITEMS remain durable but are not actively sampled. No semantic utility or learning proof.

**Next:** independent review/integration of Run95→Run96 into the full latest branch; maintain Run94 ownership. Continue another unowned canonical package (e.g. JEF/C3/Body learning source-bound integration), rather than waiting for native cgroup or Redmi. No user decision required.
