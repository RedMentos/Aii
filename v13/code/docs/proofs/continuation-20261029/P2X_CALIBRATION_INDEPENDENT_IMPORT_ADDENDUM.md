# P2X independent native replay import-path addendum — 2026-10-29

The first independent original-artifact audit [Actions 40863315508](https://github.com/RedMentos/Aii/actions/runs/40863315508) is **RED**. It successfully downloaded original ZIP SHA256 `0cef7a72655ba4e58c15ca52b0189e2bdd0b90c3f58daa69e22da2b12259d9d9`, verified ZIP CRC, all 29 inner SHA256SUMS, all 11 original stage exits and exact original head. It then failed **before any raw model-output scoring**: `cohort.validate()` imports `p0x_independent_source_holdout` as a top-level module, while the standalone CLI was launched with `PYTHONPATH=.:tests` rather than `PYTHONPATH=.:tests:scripts`. Source-only unit tests had inherited a test module's `sys.path` insertion, hiding this standalone CLI prerequisite.

Original independent RED artifact ZIP SHA256 `a05c4ec4cb50c11862354422d7eb4d1a76535fe16a9ba9cdd58fbfc136fcfa52`, CRC clean, preserved in private Library at `/V13-Checkpoints/2026-10-29/P2X-Calibration/INDEPENDENT_NATIVE_AUDIT_RED_40863315508_shaa05c4ec4.zip`; do not overwrite or reinterpret as GREEN.

**Prospective repair scope:** change only the independent replay workflow CLI invocation to include the existing `scripts` directory in PYTHONPATH, i.e. `PYTHONPATH=.:tests:scripts`. Add a source-only standalone CLI import smoke test if needed. Do not modify the original native executor, 360 frozen prompts, model, source generator, original raw, independent scorer algorithm or acceptance gates. Re-run the independent raw replay on the **same exact original ZIP**, preserve both attempts, audit original bytes and report actual result. No new model calls.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE.
