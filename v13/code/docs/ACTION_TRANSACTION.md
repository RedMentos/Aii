# WP-K: action transaction, tool contract, output commit point, provisional buffer

Module: `code/v13/transaction.py`. Hooks are in `agi/tools.py` (ToolRegistry), `runtime.py` (commit point, settle, recover) and `operator.py` (`:tx`).

## IH-H14 action transaction
- **States.** `PREPARED → COPY_COMMITTED → EXECUTING → SUCCEEDED | FAILED | UNKNOWN | CANCELLED`. Any other transition raises.
- **Copy before effect.** `ActionIntent` + `CorollaryCopy` and the COPY_COMMITTED state are written in a single SQLite transaction before the side effect starts.
- **Crash safety.** EXECUTING is persisted before the executor runs. After a crash, `recover()` (called at Runtime start) sets it to UNKNOWN and never re-runs it. A PREPARED transaction older than 1 h becomes CANCELLED.
- **Idempotency.** `idempotency_key` returns the existing transaction (`DEDUPLICATED`); the executor runs only once.
- **Undo.** A reversible tool returns `(result, {'__undo__': True, ...})`. `ToolRegistry.undo` / `:tx undo` then runs the compensating action as its own transaction.

## IH-H29 tool security contract
- **Pipeline** (`transaction.authorize`): typed schema (`{'arg':'str|int|float|bool|secret', '?' = optional}`) → user-enabled capability → risk/reversibility → per-call confirmation (always for WRITE_LOCAL/NETWORK/EXTERNAL_EFFECT and for irreversible tools) → C5 (Age right for SYSTEM/SELF origin) → executor. The steps are stored in `tx['contract']`.
- **No shell strings.** Arguments with shell syntax are refused. Tool names follow `[a-z][a-z0-9_]{1,31}`, so they stay separate from `:`-operator commands.
- **Secrets.** Only handles `{'$secret': 'api'}` are accepted. The value comes from `V13_SECRET_API` and is read only in the executor; it is redacted from result, error, state, packets and logs.
- **First WRITE_LOCAL tool.** `sandbox_note(name, text)` writes only `<home>/data/tool_sandbox/<name>.txt` and supports undo. Off by default (`:growth enable sandbox_note`) and needs `:tx approve <call>` for every call.

## IH-H12 output commit point
- The turn's message moves `DRAFT → OUTPUT_COMMITTED` right before the first visible byte (stream, direct copy and error report alike). Turn meta records `output_committed` and `output_committed_monotonic_ns`.
- After the commit, the transcript is fixed. Late evidence may only add a separate message (`transaction.correction`, `output_authority=LATE_CORRECTION`). The existing postcommit offer path keeps logging `affects_committed_output: False`.

## IH-H13 / §72 provisional buffer
- `Provisional` is a TTL scratch buffer (15 min), not the authoritative store and never a learning source (`learning_factor('PROVISIONAL') = 0`).
- At the end of a turn, `settle_turn` promotes the items through a registered sink if the turn is FINAL; otherwise they become tombstones (hash only, no payload).
- First use: tool outcomes inside a running turn (`call(..., event_id=...)`) reach AG2 grounding only after FINAL.

## Open
- Buffered-final output (Age 0 option) is not built; streaming stays the default.
- Real network or external tools are not registered yet.
- The C2/Needle tool choice belongs to WP-AG10/N4. TOOL_CALL as a C5 action candidate in the live turn is still missing.

Tests: `tests/test_transaction.py` (10). `tests/test_growth.py` was adapted: approved NETWORK calls now run as transactions.
