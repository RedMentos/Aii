# Run11 shared numeric prompt candidate native result — 2026-10-28

Owner GPT-6. PR #849 review branch; candidate source `898f43d3462fb4247648d313bec3336e30f2c4d9`, no main/owner overwrite. Original #848 public arithmetic RED `40633577048` is retained separately; the candidate is **not** the same registered cohort.

## Independent evidence

Software `40633968988`: focused 32/32, full 2218 (1 skipped), frozen runtime/focal/toolstep/model/control source blobs, compile, privacy and diff all verified. Artifact `12792194808` ZIP SHA256 `3a05e49496b1c4e02a4713c39111ce5c649978b88c66d3a06431f862d0e7e15d`, CRC and 18 internal hashes. Native Ubuntu24.04 x86_64 `40634460512`: all nine stage exit files **0** (`INSTALL, BOOTSTRAP, JEF_MODES, STEP12, ASK, ASK_META, REPORT_CHECK, PRIVACY, DIFF`), artifact `12792369642` ZIP SHA256 `14b45a4c4cab15177d2497ffb2cf2ad2b395ae06a107187f608385053f90b9db`, CRC and **27** internal hashes. Both artifacts uploaded to private Library `/V13-Checkpoints/2026-10-28/Run11-C3-Numeric-Prompt/` and byte-exact read back.

JEF `JEF_MODES_PASS`, 8/8 checks, 3/3 C2+C3 combined turns actual `C3_LANGUAGE` with C3 fallback and native C2, no B manifest; C1 restart and integrity. STEP12 `VERTICAL_CHECKS_PASS`, 8/8 checks, native C2/C3, distinct B1/B2 and persisted states, native processes released. These are **structural Linux** proofs only; `phone_measured=false`, `full_runner_proof=false`, `complementarity_proven=false`.

**Public arithmetic** `Budget 120 Euro. Berechne die Hälfte.` now returns **`The calculation is straightforward: half of 120 Euro is 60 Euro.`**, where the previous native output omitted 60. Persisted answer metadata shows `runner_role=B1_DETAIL`, `fallback=null`, `tool_call=null`, `tool_shadow=null`; native C2 selected processing route `both`. The changed EN/DE system prompt is shared by B1/B2/C3. The numeric result is a **one-case nonpaired candidate improvement**, not evidence that C3 itself performed the calculation or that other arithmetic/grounding tasks generalize.

## Next package and negative gates

Preregister a held-out multi-example bilingual arithmetic/unsupported-grounding cohort, with prompt and model pins fixed, independent seeds and negative cases. Compare baseline vs candidate without rewriting registered source/model/seed hashes; include actual runner role, tool authority, exact numeric correctness, abstention and wrong confident answers. This single 120/2 fixture must not be used to claim general utility.

Original negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY, Redmi thermal/energy/RSS long-run unmeasured, B3 receiver ablations unavailable, no whole-system completion. Exact next command: inspect current PR #849 at `9a088de8c01a1ad866e59dbdb82e346f1a4b7674`, freeze candidate prompt blob `646c6f31b52ca2664c1952af7c7e842fc3e20885` and baseline `a74d7517a7ab70e801e177b58da057e57fd3460c`, then create held-out evaluator in a new review branch. Remaining platform budget UNKNOWN.
