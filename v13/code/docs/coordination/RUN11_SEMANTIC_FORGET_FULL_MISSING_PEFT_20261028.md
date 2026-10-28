# Run11 semantic forget/encoder race — full-suite dependency RED (2026-10-28)

Source `c7a2e537b9892410bafc4f4a93c9cd44b2788a1c`, Actions `40689975127`: **18/18 focused PASS**, full `2390` tests with **4 import ERROR, 11 skipped**. All four are pre-existing Body-JEPA/LP3 import prerequisites: missing `peft` (one) and `transformers` (three). No semantic race regression was reported. Compile/privacy/diff skipped, not PASS.

Original artifact `12817515952`, ZIP SHA256 `f65bc0464285fae9156dd07e013a4096e0f3c99c860203384168c615e5d26b86`, CRC CLEAN, HEAD verified, focused.exit=0, full.exit=1. Private Library backup `/V13-Checkpoints/2026-10-28/Run11-Handoff/SEMANTIC_FULL_MISSING_PEFT_40689975127_shaF65BC046.zip`. Original RED and live-corruption RED separately preserved.

Follow-up adds pinned isolated `transformers==5.20.2`, `peft==0.21.2` and lightweight canonical software dependencies; no source/test changes. Re-run focused/full/compile/privacy/diff; no native, Redmi or Canon gate promotion.
