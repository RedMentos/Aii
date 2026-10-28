# Run11 semantic forget/encoder race — original RED checkpoint (2026-10-28)

Prereg `03c51d7f14037d951521215340cf38014a8e7ac6`; test-only `d3ab1570fef356e816a988cae03af15051dd557f`; original source-pinned Actions `40689406131` at `8923d4df800cb82e702c98495055cfb1c7a6f263`.

Original **18 focused synthetic/real-SQLite tests**: 14 PASS, **3 FAIL + 1 ERROR**. The three failures prove stale direct/cached/batch embedding keys survived a completed forget. The error proves a forgotten source triggered `ValueError: Dangling/gelöschter SourceRef` during `Memory.recall`. The fifth new live-corruption counterexample remained PASS, as did 13 pre-existing semantic tests. No full suite was run on this RED commit; skipped downstream stages are not PASS.

Original artifact `12815714649`, ZIP SHA256 `c326a23065c7046ec2b269a6c1b14b22f49ea9dc6b0a1106a4cffbba7f1565f0`; ZIP CRC CLEAN, four files `HEAD.txt`, `focused.log`, `focused.exit`, `source-sha256.txt`, source HEAD verified. Private Library backup `/V13-Checkpoints/2026-10-28/Run11-Handoff/SEMANTIC_FORGET_RED_40689406131_shaC326A230.zip` re-materialized byte-identical.

This RED is preserved. The subsequent code candidate uses Store transaction serialization to avoid cache resurrection and rechecks F1/F5 after the encoder; GREEN has not yet been measured. No native model, learning/age authority, STEP2/B3/Body-JEPA/LP3 gate or Redmi claim.
