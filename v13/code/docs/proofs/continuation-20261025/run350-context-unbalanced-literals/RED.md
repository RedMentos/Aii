# Run350 observed RED — unmatched literal source loss (2026-10-25)

- Preregistered `4afb861ac5327bd97574a0b05e8c2060a5fe5f69` before tests/source. Exact RED head `804d5c99feaa59fba45d7367c9a3a057f9b4bd79`.
- GitHub Actions `40224964445`, job `121264276746`: **37 tests, 32 PASS, 5 expected RED assertions** (unclosed inline backtick, ASCII double quote, German opener, curly opener, orphan curly closer). Balanced literal positive test and original Context OS/pin/quote tests pass. Source unmodified in RED phase.
- Raw artifact `12610548050`, downloaded ZIP SHA256 `8e09b26199ec8228142aefe8df0d2999456f226e821e25ef725235cfbc12198d`, CRC PASS, internal SHA256 manifest 3/3 PASS, embedded HEAD matches. Context OS source SHA256 `832aaea23c3790c42720d5b7174b1a90f9ec677d60005b3424d9a93d85a8ecb2`. Privacy step skipped because RED test step failed, not claimed CLEAN.
- Private Library backup verified: `/V13/checkpoints/2026-10-25/V13_Run350_Context_Literals_RED_raw_sha8e09b261.zip`.
- Next: conservative RAW fallback when an unmatched literal delimiter remains outside recognized paired code/quotes; rerun exact-head GREEN and preserve raw evidence.
