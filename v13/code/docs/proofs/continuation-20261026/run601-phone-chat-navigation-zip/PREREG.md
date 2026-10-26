# Run601 preregistration — exact-current phone source delivery with Run600 chat navigation

2026-10-26 UTC. Owner: GPT automation11. Review-only branch `codex/automation11-run601-phone-chat-navigation-zip-20261026` based on verified Run600 PR595 checkpoint `fbe462f797f2caf4feaec1c03c428daa53ff960e`, not main. This package creates a reproducible, usable Termux source ZIP including the newly tested persistent chat search/export commands; it does not add native weights.

Independent original problem: Run599 phone ZIP predates Run600 functional chat UI changes. A phone artifact must match the current source exactly, not silently distribute stale code.

Files owned: new `.github/workflows/run601-phone-chat-navigation-zip.yml` and this proof folder. Reuse pinned `scripts/package_source.py --phone-install` and `scripts/verify_phone_zip_current_run268.py` unchanged. No Canon, model, runtime, frozen cohort or original evidence edits.

Acceptance preregistered: CI checkout exact source head, pinned package and verifier hashes, original Canon SHA256, full source ZIP member parity and manifest hashes/CRC; portable packaging tests; extracted ZIP real Runtime/SQLite/Operator tests `test_run600_chat_history_navigation.py`, `test_phone_chat_sessions_run89.py`, `test_run597_chat_export_wal_snapshot.py` and `test_run598_backup_noclobber.py`; privacy scan; SHA-closed original raw and actual ZIP artifact even if RED. Independently verify downloaded artifact bytes and nested ZIP after CI. Preserve initial failures.

Scope: Linux software source-only, no models, no Redmi, no native C3/B1/B2/Body-JEPA training, no promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. Full-suite Run596 RED retained. No public user data, no Drive rejected destination, no force push.