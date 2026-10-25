# Run344 RED verified and independently archived (before patch)

- Exact head `d5dc9177c52c06d316e74c7ae225314bef25368c`.
- GitHub Actions `40222405681`, job `121256612277`: **FAILURE**, 37 real Runtime/SQLite tests, **5 failures**, no errors. The five new failures are conflicting status/payload accepted, duplicate concurrent packets, duplicate after restart, orphan packet after SQL UPDATE failure, and duplicate exact replay. Unknown action/nonfinite negative control passed; existing C5/World/Store tests in selection passed.
- Raw artifact `12610295881` downloaded independently; ZIP SHA256 `3cdde730034feaca909c285d479a2834be1952025bc4c8453ad51f4c7e06d13c`; CRC clean, 3/3 internal SHA256 manifest entries verified; embedded HEAD matches.
- Private Library backup uploaded successfully at `/V13/checkpoints/2026-10-25/V13_Run344_ActionOutcome_RED_raw_sha3cdde730.zip`.
- No production patch or authority promotion at RED checkpoint. Next: replace `Store.finish_action` with one transaction that validates prior receipt and commits action row + packet atomically; fail closed on conflict/orphan.
