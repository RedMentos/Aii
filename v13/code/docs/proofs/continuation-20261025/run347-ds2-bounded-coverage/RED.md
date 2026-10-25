# Run347 RED before new policy implementation

- Exact head `d89cb8c26f7e96ad13f77f8c1dd788331c7a76e5`.
- Actions `40223342751`, job `121259452492`: **FAILURE**, 17 tests, 5 failures, all new cases because `lp_goal_coverage` is not registered; original DS1/Run346 tests pass.
- Frozen fresh seeds 501..520 evaluation was correctly skipped at RED. No policy source modified yet, no utility claim.
- Raw artifact `12609912114` ZIP SHA256 `3c930178f59675e438916d3f97f5697bcc9aa72d90902af1494f8d789d04198d`; independently downloaded, CRC and 3/3 manifest hashes verified, embedded HEAD matched. Private backup `/V13/checkpoints/2026-10-25/V13_Run347_DS2_Coverage_RED_raw_sha3c930178.zip`.
- Next: minimal frozen bonus+gate implementation in `sandbox.py`, rerun exact-head tests and fresh 20-seed cohort. Keep Run346 NOT_SUPPORTED immutable.
