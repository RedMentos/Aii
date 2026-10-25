# Run122 independent source ZIP cross-review

2026-10-25 UTC. Before edit, reviewed Run121 PR #152 (Linux RED→GREEN CLI fix) and Run120 PR #151 (source-only unpack smoke). The Run122 exact PR head `3d2a7a33db6cfc230865961af61a8c00ecb9c730` was packaged by existing `scripts/package_source.py --phone-install`, **not** an ephemeral merge ref.

First CI run 40147471413 FAILED because the preregistered `test_phone_halt.py` does not exist in this integrated source. The other 20 extracted tests had passed. This failure is preserved verbatim; amended protocol does not count the missing test as passing.

Second CI run 40147565614: official privacy CLEAN; 845 source files + manifest; source ZIP 12,601,444 bytes, SHA-256 `2aa8c40771c3db426ebe0e938ee176262cf495f8a4076914dc143fe3b5f825c1`; 20/20 real extracted Linux CLI/operator/standstill tests PASS. Artifact ID 12580984168, wrapper SHA-256 `85d2a507e2cd32b4c582b2bab0028130f1b81520613878f57d84faffd4ce285d`.

Independent verification: downloaded the actual GitHub artifact via connected GitHub, checked wrapper/inner ZIP CRC and both SHA-256 values byte-for-byte, extracted to clean container, ran the same 20 tests on local Python 3.13.5; 20/20 PASS. This is an additional Linux software check, not native or Redmi proof.

**Open:** Claude WP-UI1 files on `claude/project-thread-e53fle` (phone_halt.py, Widget installer, guide/tests) are missing from the integrated review chain; do not claim they are installed. Next: selective import and tests under a separate owner. STEP2/B3/JEPA/DS2/full-system gates remain negative.
