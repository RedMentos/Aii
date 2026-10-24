# Run95 result / BUILD_STATE delta — bounded Sleep replay index

2026-10-24. Base Run93 `b54342c1278f78f509359b6daa8dd644e6f3a5d9`. PR #127, branch `codex/sleep-replay-window-run95-20261024`. Run94 World Model ownership untouched.

**Preregistered RED:** test-only commit `9af6220496181b4e4a535a7a7a55dc27186124ba`, Actions run 40136694880/job 120999601567: 3/3 new SQLite counterexamples FAIL, 32/32 inherited Sleep/Homeostasis controls PASS. Full raw logs retained in Actions; bounded excerpt in CI_RED_RAW_EXCERPT.log.

**Fix:** `ReplayQueue.sync` selects the newest MAX_ITEMS replay/event rows by `r.created DESC, r.id DESC` (tie stable), restores chronological processing among selected entries, marks out-of-window state entries `WINDOW_EVICTED`, and evicts only out-of-window entries when bounding the schedule. Original replay rows, source refs, protected in-window histories and Age/Dream authorities remain untouched.

**Cross-review:** added regression ensuring an already retired in-window row is not deleted and reintroduced with reset reps, an in-window protected-old item retains its repetition count, and all replay rows survive eviction. Four new real SQLite tests.

**GREEN:** isolated Actions run 40136868301 / job 121000139969 SUCCESS: **36/36** Sleep/SQLite/Homeostasis tests PASS, compileall PASS, official public-repo privacy scan CLEAN. Initial post-fix run 40136760369 had 35/35 PASS but privacy scan ERROR because test-only workflow used shallow checkout; fixed with fetch-depth 50, and subsequent runs scanned successfully. Latest broad focused source/ZIP workflow run 40136868317 is PENDING at checkpoint, not claimed passed.

**Primary source:** SQLite SELECT ORDER BY/LIMIT documentation, https://www.sqlite.org/lang_select.html (consulted 2026-10-24): explicit tie-break needed for deterministic boundary selection.

**Evidence class:** real Linux SQLite/software only, no native model, no Redmi, no learned semantic utility. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a FAIL, Z8 FAIL, full V13 INCOMPLETE. Source/blueprint/registered cohorts unchanged.

**Open:** capacity policy remains a bounded 2048-item *active* window; older protected corrections remain in durable replay but can fall out of active rehearsal. A stratified long-term retention policy would need separate preregistered comparison. Native/Redmi gates unchanged.

**Next independent package:** examine fresh correction wake scheduling before full Sleep cycle: `SleepRuntime.tick` reads the persisted schedule without synchronizing newly inserted replay rows. Preregister a real SQLite/Runtime counterexample and ensure no background or Age bypass. Do not overlap Run94 World Model owner. No user decision needed.
