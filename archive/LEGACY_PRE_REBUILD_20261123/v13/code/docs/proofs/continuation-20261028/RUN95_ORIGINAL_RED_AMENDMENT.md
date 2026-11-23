# Run95 original RED and preregistered correction (2026-10-29)

Original prereg FIRST commit `f86e5971808053636c018e68520950c7de9c9de5`. Original exact workflow head `d2993eb812bf1d05af39170b6cc21ad9371c3d9a`, Actions `40793018105` FAILED. Original artifact ID `12863070057`, ZIP SHA256 `0917dbcaab6fb2fa6c2b29a78f359d4908fb1f88830e92fec0e47b6578e18f46`, CRC clean, 15/15 inner SHA256SUMS independently verified, SOURCE/INSTALL/PRIVACY/DIFF exit 0; COMPILE exit 1, FOCUSED/FULL SKIPPED_RED. Private Library backup `/V13-Checkpoints/2026-10-29/Run95-Human-Source/V13_Run95_ORIGINAL_RED_40793018105.zip`. This was **not** a runtime/semantic failure: no test executed.

Root cause: the new `Operator.run` dispatch was inserted with literal `\\n` escape characters instead of real newline separators. `COMPILE_RAW.log` shows SyntaxError at `operator.py:96` (`unexpected character after line continuation character`). Correct only those three dispatch lines, leaving command behavior and fixed test fixtures unchanged.

Separately, Run93's original full-suite RED showed that this base's full test discovery needs pinned CPU `torch==2.14.1`, `transformers==5.20.2`, `peft==0.21.2` as in independently GREEN Run91 #998. The Run95 initial compile failure prevented reaching the full suite. Add these exact isolated test dependencies before the corrected full suite; no native model download or training.

Preserve the original RED and separately close/hash the corrected run. No Age/STEP2/B3/Body-JEPA/LP3/jepa_weight/Redmi or whole-system promotion.