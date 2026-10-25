# Run307 — Sleep A exact-correction retention: RED → GREEN (actual SQLite)

UTC 2026-10-25. Draft PR305, base Run306 verified checkpoint `a7c4193f9e53b742adaec13dcf9f42c4a807544a`. Independent owner `sleep.py`, new tests, CI and scoped proof only. No Runtime/Store/native/model/Canon/seed/approval edits.

## Defect and evidence
- Old `SleepCycle._probe` counted a correction as recalled when **another correction had the same answer value**. Actual Runtime/Store reproduction: two active, independently F5 source-bound corrections from one event, distinct cue keys, same synthetic value; `memory_top_k=1` returns one ID. Old probe reported both checks PASS. A real `sleep_a` replay of that event also reported PASS/reps despite missing one correction.
- Preregistration `6aff53fa2c190771a186ab22236239c206d99224`, RED tests `164be0afb9ae11b94df6352e2f43bf40019d8bcf`, CI `2b77d81f7f808a23ff2c150dea4b3912940f499c` were committed before modifying source.
- **RED** exact source `2b77d81f7f808a23ff2c150dea4b3912940f499c`, Actions `40205973171`: **33 tests, 2 expected FAIL** (exact memory identity and actual Sleep A false PASS), remaining tests pass; official privacy CLEAN. Closed raw artifact `12603558061`, SHA256 `ab12f705b1eb8c58aee4c33164e733c5efb54473a5f68a4b165d2dfc9e47c7b0`.
- **GREEN** code commit `9cce2b793491f1331d9891e189d7983488fbf7a9`, `sleep.py` blob `8b5d4ddc49dbf4ac60aa780ffd37ce320dab9e31`; Actions `40206052739`: **33/33 PASS**, official privacy CLEAN. Closed raw artifact `12602939532`, SHA256 `6ca84bd8efe1b1c0512748ab4d452fb6f15e4a1c1b6ed12232bd2406a746b0a6`.
- Minimal fix: require exact `memory_id` in `Memory.recall` results for every active correction; source/value integrity remains separately verified. With top-k=1, one missing ID now produces `RECALL_MISS`, Sleep A `failed=1`, `reps=0`; with top-k=2, both pass. After forgetting one correction, the remaining one still passes.
- Independent Linux software review of the same one-line logic on extracted source: actual SQLite scenario returned FAIL with one missing ID; **11/11** existing Sleep memory-authority/offline tests passed. Original Sleep replay, authority, policy and backup continuity regressions passed in dedicated CI.
- Both RED/GREEN artifacts downloaded, original SHA256SUMS verified, uploaded to private Library `/V13-Inquisition/Proofs/Run307/`, then read back byte-for-byte with SHA256 parity. No rejected anyone-writable Drive destination used.

## Limits / next
This is truthful software retrieval-level retention, **not native model memory, weight learning, Redmi measurement or JEPA utility**. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE` unchanged. PR305 is review-scoped, not merged into main.

Next: select a different substantive Canon package outside Sleep/WorldModel/backup; keep Run297 native and Run303 Budget owners isolated. The Run305 source-only Termux ZIP is byte-verified but predates Run306–307; regenerate only after a meaningful integration checkpoint, without inventing native proof. Full-suite baseline `40202886433` remains FAILED (2 failures, 36 errors).
