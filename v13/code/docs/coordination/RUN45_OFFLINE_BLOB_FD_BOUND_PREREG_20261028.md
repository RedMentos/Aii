# Run45 — bounded descriptor reads for offline SHADOW blobs (2026-10-28)

**Parent:** Run44 review-only #952 at exact `07f31a288cbade3779b791b22b2d4b10ffb8ba59`. Independent child branch, no edits to Run44 owner branch, main, frozen native/STEP2 source, registered models/seeds, production Runtime/Store or Canon.

**Problem / counterexample:** Run44 verifies `Path.stat().st_size <= MAX_BLOB` and `is_symlink() == False` before calling `Path.read_bytes()`. A concurrent replacement or growth between checks and read can follow a newly introduced symlink or allocate beyond the 64 MiB bound. The diagnostic is intended to be offline, but a fail-closed file reader should not rely on this pathname TOCTOU window. The same issue affects plain and zlib-packed blobs. The source hash does protect decision integrity but not resource usage or unwanted filesystem reads.

**Candidate:** retain existing Run44 interface/CLI and result schema; replace only blob file access with one descriptor-based, `O_NOFOLLOW | O_NONBLOCK` regular-file reader, `fstat` and a hard `MAX_BLOB+1` read cap, with descriptor close in all paths. Reject symlink/FIFO/device/non-regular files and oversized content. Do not change SQLite or source/decision logic, evidence level, or output authority. No new external dependencies.

**Proof before code:** add isolated regression for bounded plain/packed file reads, symlink/FIFO rejection, and a deterministic `Path.read_bytes` monkeypatch proving the diagnostic never delegates an unbounded pathname read. Preserve existing Run44 9 + real-Store 2 tests. Source-only CI on this branch with pinned Run44 ancestors, focused/full suite, privacy and diff check, raw logs/sha256. Red-first test may initially fail because the new helper is absent. No native model/Redmi run or gate promotion.

**Gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; V13 incomplete. Current platform remaining budget UNKNOWN.
