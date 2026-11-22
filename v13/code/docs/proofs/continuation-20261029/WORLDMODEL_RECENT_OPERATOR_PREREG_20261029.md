# World-Model recent observed event IDs — preregistration 2026-10-29

Parent PR #1159 verified source checkpoint
`1f757e8084ca612237e52689d7a1fe046f86b033`.

## Functional need
The new `:worldmodel compare <Event-ID>` read-only view requires an
operator-visible event ID. The existing command has no local discovery.
Implement `:worldmodel recent` returning at most eight current-session
completed observed action event IDs (no user text, no other session's events,
no model calls). Each listed ID is usable with the comparison command.
No action selection, learning or authority.

## Tests frozen before run
- Empty current session => empty list and no fabricated events.
- Insert 10 completed observed forecast actions in current session and
  two in a foreign session; at most 8 IDs returned, all current-session,
  no foreign IDs, no source text.
- All existing `:worldmodel event`, `:worldmodel compare`, no-fit and
  foreign-session rejection tests still pass.
- Check Store World fit state, packets, actions, Age0 mode, runner PIDs
  unchanged by read-only recent call.
- Focused CI, Canon hash, compile, privacy scan, diff, raw SHA256SUMS.
- No new model, seed, cohort, weight, STEP2/B3/JEPA gate promotion.
