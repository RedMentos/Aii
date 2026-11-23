# SQLite migrations and accepted user turns

Canon STEP 0 remains the source of scope. This implements migrations and the
existing bounded turn queue inside the owned SQLite substrate. It adds no model
or architecture layer. `Store.SCHEMA_VERSION` is now 2.

## Database migration

- Version 0 → 1 creates the historical tables plus a migration journal.
- Version 1 → 2 creates `accepted_turns` and its FIFO state index. Existing
  version-1 data, immutable generation manifests, blobs, checkpoints and model
  caches remain intact. Historical events without a durable queue record are
  preserved; they are not guessed to be pending model requests.
- Each transition uses `BEGIN IMMEDIATE`. Table creation, structure/FK/index
  validation, migration journal insertion and `PRAGMA user_version` share one
  commit. No `executescript` implicit commit is used during migration.
- A failed transition rolls back entirely. The next startup resumes from the
  last committed version. Future versions fail before journal-mode or database
  mutations. Startup failures close both SQLite and the exclusive coordinator
  lock, allowing a corrected database to be reopened.
- Audits compare actual owned columns, primary keys, foreign keys, indexes and
  table constraints to the declared schema and perform SQLite integrity and
  foreign-key checks. They refuse damaged structures rather than silently
  constructing a misleading partially repaired schema.
- Backup hashes authenticate the original archive first. A verified v1 staging
  copy is upgraded transactionally before the restart-safe directory swap.
  Backups from v2 are also accepted. Unsupported versions remain rejected.

## Runtime integration interface

`accept_turn(session, text, queue_count, queue_bytes, input_bytes,
request_key=None)` returns the existing `EventEnvelope`. Admission checks,
source metadata, event, immutable user message and queue record share one SQLite
transaction. Rejected admission creates none of those rows. A failed SQL commit
can leave an unreferenced content-addressed blob; it cannot create accepted work.

`pending_turns(limit=None)` returns FIFO rows containing `event_id`, `bytes`,
`accepted_at` in Unix wall seconds and the original envelope in `event`.
`queue_stats()` returns waiting count/bytes and persisted pause. FIFO ordering
uses a SQLite sequence, independently of clock movement. Queue TTL must compare
wall time across restart; monotonic timestamps from a prior process cannot be
used for that comparison.

`claim_turn(event_id)` atomically changes the first pending turn to `RUNNING`.
It refuses a persisted pause, a second running turn, stale/double claims and
revoked sources. `finish_turn(event_id, status)` CAS-finishes pending/running work;
`FINAL` maps to `DONE`. Repeating a terminal completion returns false.
`set_queue_paused(bool)` and `queue_paused()` persist operator pause separately
from temporary thread wakeups.

An optional bounded request key retries the same exact session/text without a
second event. Reuse for different text/session fails. Identical text intentionally
sent without such a key remains two distinct user turns.

## Crash semantics and limits

Pending turns and pause survive abrupt process death. A previously running turn
with a persisted terminal assistant is reconciled to its terminal state. A turn
without such output becomes `INTERRUPTED`; partial text also becomes
`INTERRUPTED`. It is not automatically executed a second time. This prevents
repeated native output after a crash between streaming and completion. A new
explicit user submission may retry it. Deleted-source pending turns are cancelled.

The durable queue applies to accepted user turns. Download, training, replay and
probe control jobs keep their existing explicit lifecycle and are not implicitly
re-executed by this queue. Runtime still needs to use the APIs for admission,
claim, terminal completion and persisted pause; in-memory thread queues are only
wake/caching machinery once integrated.

## Actual proofs

`docs/proofs/persistent-queue-migrations-unit-20261004.log` records actual SQLite
unit checks: fresh and legacy migrations, denied mid-transition DDL rollback,
future-version byte preservation and lock release, malformed schema rejection,
v1 backup/restore, transaction-trigger admission failure, UTF-8 count/byte bounds,
concurrent admission, stable request-key dedup, FIFO/pause/restart, revocation,
completion crash window, and subprocess `os._exit(23)` with saved partial output.
These are substrate proofs, not new phone inference or sustained thermal proofs.
