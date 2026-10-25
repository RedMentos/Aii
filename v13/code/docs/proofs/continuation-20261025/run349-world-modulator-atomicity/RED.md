# Run349 observed RED — split digital-error/outcome commit (2026-10-25)

- Prereg `d3c9f6bf0a1ba6e84293f6fda837327d98a546a1` before tests/source. Exact-head `3a27543f572858a58a4e87fee73c0deb4f823e1e`.
- GitHub Actions `40224590727`, job `121263159701`: **FAILURE** with **23 tests, 22 PASS, 1 expected RED**. New `test_abort_prediction_insert_rolls_back_modulator_as_a_pair` proves the orphan: SQLite trigger aborts `PredictionOutcome` but `ModulatorPacket` remains committed. Other two new tests and original WorldState/Run343/Run109/Run298 regression tests pass.
- Raw artifact `12611125381`, downloaded ZIP SHA256 `43f763701a19aced8b535dad559abac86eac4ed5efd5b6e0aea984a0c2364154`, CRC PASS, 3/3 internal manifest hashes verified, embedded HEAD matches, source SHA256 `d5181f860566da27319f8c10079ebf3a2338bc7f96d7f9d86d6c991f44cd1ed8`. Privacy step skipped due expected RED, not claimed CLEAN.
- Private Library backup verified at `/V13/checkpoints/2026-10-25/V13_Run349_World_Modulator_RED_raw_sha43f76370.zip`.
- Next: construct both packets and commit in a single SQLite transaction with inside-transaction action-id receipt recheck, preserve missing/invalid-score non-promotion; run exact-head GREEN, privacy and independent raw audit.
