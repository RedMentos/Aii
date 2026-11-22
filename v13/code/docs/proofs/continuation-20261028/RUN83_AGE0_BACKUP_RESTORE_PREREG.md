# Run83 prereg — Age0 operator backup → offline restore → source recall (2026-10-28)

Owner GPT-6 scheduled continuation. Review-only child of Run82 #989 head `a8842df7107e11fb55ba429405078e93b5a41ba4` (parent CI pending at preregistration). This is **real Linux Runtime/Store/Operator backup/restore**, no native model, no user files, no external network. No production source change or gate promotion.

## Fixed test plan

1. Fresh temporary home; real Runtime with sleep disabled, operator `:status` learning `RECORD_ONLY`. Record exact source-backed fact A (`Project Elyra budget = 615 Euro`) through Store.event + Memory.feedback permission=record; `:verified` for Elyra READY with zero native calls.
2. Call real operator `:backup`, verify tar.gz exists under this home, checksum file bytes and validate `backup_manifest.json` format, member hashes, and `models_included=false` using standard tarfile/hashlib. Do not edit archive after creation.
3. Add fact B (`Project Dovan budget = 700 Euro`) after snapshot; source-backed `:verified` for Dovan READY. Close Runtime fully.
4. Attempt offline restore from deliberately invalid non-tar file and require refusal **without changing live B**. Reopen real Runtime, Dovan READY; close. Then offline `v13.backup.restore(home, snapshot)` (equivalent to explicit confirmed offline restore) and verify it creates a safety backup.
5. Reopen real Runtime; Elyra READY with same original memory id; Dovan CLARIFY, no native calls. Reopen again to verify persisted restored state and unchanged Age0 RECORD_ONLY.
6. No model downloads, no shell/network tools, no production weights, no permission/age promotions. Source-bound CI runs new E2E, parent Run82 E2E, backup/restore regressions, full software suite, privacy and closed original raw SHA256SUMS. A software PASS is not native/Redmi/whole-system completion.

If parent Run82 RED, child cannot integrate. Preserve all negative gates (STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0). The operator `:restore` remains an offline command by design; no in-process restore is attempted.
