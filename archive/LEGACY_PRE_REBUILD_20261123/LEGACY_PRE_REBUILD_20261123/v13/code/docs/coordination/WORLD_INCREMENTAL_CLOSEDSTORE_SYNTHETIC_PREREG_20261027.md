# World-JEPA closed-store end-to-end 400-step synthetic SQLite proof — prereg (2026-10-27)

Review-only PR #769, parent #758, after focused software PASS. This is a **new explicitly synthetic SQLite fixture** and must not replace or relabel the original #764 synthetic cohort or any real observed/private-store result. No native/Redmi or real-world utility claim.

Freeze source blobs: World-JEPA `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`; digital bridge `4ab37e11d8238d376e568567f901c85c12d09da8`; incremental probe `841a99e86099dc153a322717510a5c4e4aaffe0d`; closed-store CLI `088528535d887b10f5786a8c176002c20f4c013d`. Use `tests.test_world_jepa_readonly_store.fixture` with n64 deterministic rows in a temporary closed SQLite database, then call `run_db(db_path)` with the **unchanged default** steps400, seeds3/7, ensemble3, ridge lambda0.01. Require no DB byte mutation, no WAL/SHM/journal, 47/17 train/heldout, finite aggregate JSON, no raw IDs/paths, no Age authority or utility promotion. Store only aggregate JSON and raw exits/HEAD/source hashes in CI artifact. A failure remains a failure; do not silently lower steps or alter original model/cohort.

This run proves only the software end-to-end path through a closed synthetic SQLite file, **not** a real observed V13 store, not incremental benefit, and not mobile feasibility. Independent review remains required.
