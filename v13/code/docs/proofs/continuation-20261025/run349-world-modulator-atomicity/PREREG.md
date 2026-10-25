# Run349 preregistration — WorldState paired modulator/outcome atomicity (2026-10-25)

Base: Run348 review head `f4d8d9710c664cd51f17e889895565117e2a9ba1`, building on Run347/PR343 and Run345/PR341, not production main. Owner: `v13/code/v13/world.py`, new `v13/code/tests/test_world_modulator_atomicity_run349.py`, new workflow and this proof folder. Do not modify active DS2, Store action receipt, registered native cohorts, source/model/seed hashes, age/approval/learning gates.

## Observed code-level crash window
`WorldState.observe` currently writes a digital-error `ModulatorPacket` in its own SQLite transaction and later writes the authoritative `PredictionOutcome` in a separate transaction. If the second INSERT fails after the first commits, restart/retry can emit a second modulator for the same action. This is not a native-learning result; it is a durable own-outcome integrity issue.

## Frozen RED→GREEN tests
- Construct a real Runtime/Store SQLite synthetic `SOURCE_COPY` action with authoritative event, ActionIntent, CorollaryCopy, finalized Self-Candidate, exact source refs and finite fake world score (mocked scorer, **no native model**).
- Install a SQLite `BEFORE INSERT` trigger that aborts only `PredictionOutcome` writes. RED: an orphan `ModulatorPacket` survives; GREEN: the transaction rolls back both packets. Preserve original action, intent and corollary, never invent a successful observation.
- Remove trigger and retry; exactly one `ModulatorPacket` and one `PredictionOutcome` survive, `observed_action_count=1`. Restart and retry remain exactly-once.
- A failed/invalid latent score still permits a non-scored own-action `PredictionOutcome` without a digital-error modulator or fabricated semantic truth. Existing `test_world_state`, `test_world_multiaction_recovery_run343`, `test_world_recovery_invalid_run109`, `test_world_terminal_outcomes_run298` remain green.
- Preserve raw RED/GREEN exact-head Actions, source SHA256, privacy scan and independently verified ZIP CRC/internal SHA manifest, private backup. No World-JEPA, B3, STEP2, native, Redmi, Age, approval or V13 promotion.

Minimal repair: construct and validate both packets, then commit in one Store SQLite transaction with a second inside-transaction action-id receipt check; materialized WorldState refresh remains recoverable after commit. Keep the existing negative score handling, and preserve the historical raw evidence.
