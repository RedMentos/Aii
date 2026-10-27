# Current integrated Z1 + JEF + BP11 source-only phone ZIP — prereg (2026-10-27)

Owner GPT-6 automation, review-only child of PR #699 exact head `9b22126e38d68f07520e4696d9efcc0aba6bf3c5`. This branch changes only workflow + scoped evidence; no Runtime, model, source, canonical document or safety gate edits. Existing source package scripts `v13/code/scripts/package_source.py` and `verify_phone_zip_current_run268.py` are used unchanged.

Goal: provide a verifiable **Termux source-only package**, not an Android APK or native phone benchmark, from the newest integrated Z1 gate, JEF goal receipt and BP11 module safety tree. Build with `--phone-install`, independently verify every source ZIP member and negative gates, extract and run 102 focused software tests + portable `v13 selftest` from the extracted package. Preserve raw exit/logs, exact HEAD/source ZIP hash and source lineage. No models downloaded, no tool/model execution, no permissions promoted. Avoid publishing private data or weights.

Known historical full suite RED (5 FAIL/73 ERROR on five-parent baseline); no whole-system acceptance claim from extracted smoke. If any ZIP member is missing or any extracted test fails, retain RED and do not claim a usable package. Next: user-run Redmi sustained validation and native model/runtime proofs remain separate.
