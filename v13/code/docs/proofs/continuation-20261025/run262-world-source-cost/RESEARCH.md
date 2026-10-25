# Run262 research — source-bound state cache invalidation is not trivial (2026-10-25)

Scope: hypothesis only; **no code integration, no performance or security gate promotion**.

Primary SQLite references, checked 2026-10-25:
- SQLite official `PRAGMA data_version`: https://sqlite.org/pragma.html#pragma_data_version — changes made by **other connections** change the value on the observing connection, but same-connection commits do **not**. Values cannot be compared across different connections.
- SQLite official `sqlite3_total_changes()`: https://sqlite.org/c3ref/total_changes.html — tracks changes made on **that connection** (including triggers), but not changes from other connections. The documentation explicitly recommends `data_version` for other-connection writes. Its value is not meaningful under unsynchronized concurrent access on the same connection.

A candidate cache key could include connection identity + same-connection `total_changes` + same-connection `PRAGMA data_version` and an epoch that changes on restore/reopen. **This is not sufficient as a security proof**: it does not authenticate externally replaced database bytes, directly tampered blobs, or untracked source files; same-connection concurrent writes require synchronization. A malicious writer could also recompute the current unkeyed model SHA256, already acknowledged in PR259.

Before any performance optimization, preregister and test: source deletion/rewrite, ActionSelection packet change, action status/outcome change, source blob mutation, second connection commit, same connection commit, rollback, backup/restore, process restart, database file replacement, and races between validation and use. Every untracked case must fall back to full source revalidation or refuse; no stale model authority.

Run262 measured per-call `load` median 2.44 ms at 16 rows and 140.67 ms at 1024 rows on GitHub Linux actual Store with synthetic actions. This motivates investigation, **not** a permission to weaken revocation checks or extrapolate to Redmi.
