# Run102 RESULT — Fixed user-rule non-disclosure SEND safety

**Scope:** `userrules.py` fixed SEND lexicon only, real Runtime/SQLite tests, isolated workflow, proof files. Based on Run101 `71d2fcbdda23d7cc68ad4e5c50915d9eb5074227`; no edits to Callosum/JEF/Sleep/World/Context/ToolStep, Canon, model or Age gates.

**First RED:** Test-only `9e1ee8574892ad619c005932827193bb0d3630c4`, Actions run `40140113032`, job `121009882971`: 42 tests, four expected FAIL. `Do not expose/reveal/divulge/broadcast my phone number` were stored as FORBID but parsed only as CONTACT, so a declared SEND+CONTACTS effect was incorrectly ALLOW. Three positive controls and 35 inherited G1–G6/prohibition tests PASS. Raw excerpt preserved in `CI_RED_RAW_EXCERPT.log`.

**First GREEN:** `88d0a943127b2ea7bd3886a4b03acd9a9dfbd852`, `userrules.py` Git blob `6f0f2b29b27056005afed99058ba38744a1e78cd`: four disclosure stems added to SEND; Actions `40140184096` job `121010101534`: 42/42 PASS, official privacy CLEAN. Original full log and `CI_FIRST_GREEN_RAW_EXCERPT.log` retained.

**Independent review RED:** Additional common user phrasings `Do not show/display/distribute/circulate my phone number` were also FAIL-OPEN. Explicitly preregistered in `REVIEW_EXTENSION_PREREG.md` **after** the first GREEN, not backdated. New tests-only commit `0c013264cd7764e85f78339ad6ed9de624464f56`, Actions `40140288684` job `121010414674`: 46 tests, four new expected FAIL; raw excerpt preserved in `CI_REVIEW_RED_RAW_EXCERPT.log`.

**Final fix:** `132c319564860e03d162be8aef6f6bd50f8a08f3`, exact `userrules.py` Git blob `0dbb351d318f24ee119a966db127e4668dfdb8e0`: add `display/distribut/circulat` stems and exact `show/shows/showed/shown/showing` words to SEND (avoids broad `show*` stem). Existing parser, statuses, open ASK, explicit loosening and G1–G6 unchanged.

**Final CI:** Targeted Actions `40140372556` job `121010724204`: 46/46 PASS and official privacy CLEAN. Broad Actions `40140372565` job `121010664423`: 401/401 selected Linux SQLite/software tests PASS, privacy CLEAN; model-free source ZIP audited (824 files, SHA256 `9ade24187de3ed46a73ab98f988deb09c9e4913f9fb94c67f44e238a1b617eb8`), extracted ZIP 100/100 PASS, Runtime SQLite restart PASS. Full raw logs remain in Actions; `CI_FINAL_GREEN_RAW_EXCERPT.log` contains original selected lines. Local independent verification matched the exact final Git blob SHA, inherited 46 tests PASS, five disclosure verbs plus four review verbs DENY before and after SQLite restart, positive request and UNCLEAR ASK preserved.

**Claim boundary:** SEND action was a **synthetic declared policy effect**, not a real external communication. This proves fixed parser + persisted rule + verdict for these phrases only. Unknown paraphrases remain; model-generated rules cannot loosen anything. Existing user-rule enforcement still covers registered tools only; autonomous learning/memory paths are not globally gated. No Age, native model, Redmi or AGI utility claim.

**Original gates:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Z6a/Z8 failures; full V13 INCOMPLETE. PR remains isolated, not production merged.

**Next:** after independent review and owner freshness check, implement a separate canonical user-rule `LEARN/WRITE` guard for explicit `Memory.feedback` and `Memory.retrieval_feedback`, test-first with actual SQLite and no side effects on denial. Explicitly state other learning paths remain unguarded; do not misrepresent as global consent enforcement. No new user decision; rejected anyone-writable Drive backup not used.
