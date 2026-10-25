# Run345 verified RED before production patch

- Exact head `c111896803bd2c47840c2d6501edc240b9ea8895`.
- Actions `40222747784`, job `121257655942`: **FAILURE**, 29 tests, 3 failures, no errors.
- New RED cases: SQL actions INSERT abort leaves both ActionIntent and CorollaryCopy packets; CorollaryCopy INSERT abort leaves an orphan ActionIntent; mismatched event generation is accepted. Existing success, concurrent action and restart controls passed; existing C5/World regressions passed.
- Raw ZIP artifact `12609652984`, independently downloaded SHA256 `5c17e6f0d97575e313c5ba12400dd9d039e8e9ea5cdbaa7a1d06c09b63496329`; CRC and all 3/3 internal manifest entries verified, embedded head matched.
- Private Library backup confirmed at `/V13/checkpoints/2026-10-25/V13_Run345_ActionIntent_RED_raw_sha5c17e6f0.zip`.
- No production patch or gate promotion yet. Next: one SQLite transaction for intent/corollary/action row, event+generation check before packet insertion, rerun exact-head CI.
