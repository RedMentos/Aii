# WP-N8 A1 episode vector boundary integrity — review checkpoint

Date 2026-10-27 UTC. Owner GPT-6 continuation. **Review-only** child PR #743 of PR #742, original parent `0047aa76d5e5d221f18c0e4d4ce36c14bcb70f46`. Prereg `5dcea9830a871debab3402b976b7e0ed8d9edf08` before RED tests and source repair. Canon, model/seed/source hashes and all registered cohorts unchanged.

## Reproduced defects

1. Same-text episode vectors of unequal dimensions (`[1,0]` versus `[1,0,100]`) were compared with `zip`-truncated dot products and full-length norms. This fabricated a high context shift and a false boundary where lexical fallback should have been 0.
2. A NaN episode vector reached strict JSON persistence, raising an exception instead of recording an event with unavailable semantic signal. Bool/nonnumeric/zero vectors were likewise not consistently rejected.

Repair: `valid_episode_vector` requires nonempty list/tuple of finite real non-bool coordinates and a nonzero finite stable norm. `Episodes.observe` drops malformed vectors and validates after rounding; `signals` compares semantic vectors only when both are valid and dimensions equal, otherwise uses the existing lexical fallback. `cosine` now divides by stable `math.hypot` norms before dot product. Valid same-dimensional semantic shifts remain observable. No authority, model or learning behavior is promoted.

## Exact evidence

- Initial RED Actions `40539508967` source `9fa515a33d99058becc87dc8a81908b2f8af75fe`: 18 tests, 1 FAIL + 1 ERROR, original workflow before source-blob binding correction. Raw ZIP `12750056799`, SHA256 `e2822c3c73a7dbdb5bc207a7f32ca1d1c89f5ddf08f5185b6a46a7211af86b83`; preserved privately.
- Correctly bound RED Actions `40539550940` source `400715b76c8bdedf68b5be24ec6211102e077f3f`, original episodes blob `48354f1f1764d76228f923ebc89e567e73331f3e`: 18 tests, 1 expected FAIL + 1 expected ERROR, INSTALL/COMPILE/PRIVACY/DIFF 0, UNIT 1. Artifact `12749208413`, ZIP SHA256 `933bf72474019b7676d52c9dcc16623873122aff0d182a75943baa0fb2c8a189`, CRC clean, private backup.
- GREEN focused Actions `40540134459` exact source `8d84592e5f01032ef0bd7bbd2094e7bf7468668d`, episodes blob `b994e03a58f33e2632d444d9ec5a5415dbc0de2f`: **18/18 PASS**, all five exits 0, artifact `12751075809`, ZIP SHA256 `f3f071ce1eab512a089d52fbab661297a0904d9f01ef71ffd3fc0a208d3488a5`, CRC clean, private backup.
- Full software suite workflow source `28ccbe8c6ebed2ced0443ee40a639ff30f8db420`, Actions `40540186361`: **PENDING** at this checkpoint, no full-suite claim.

Private artifacts stored under `/V13-Checkpoints/2026-10-27/Automation11M-Episode-Vector/`, not published in the public repository. GitHub proof metadata contains synthetic test identifiers only.

## Gates / next

LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured, whole V13 incomplete. Software integrity only, no real semantic quality or JEPA utility claim. Next: inspect exact-source full-suite Actions `40540186361` raw exits, CRC/hash and byte-verify private backup, update report/state, independent review PR #743. Continue another distinct canonical work package, not automatic main merge.
