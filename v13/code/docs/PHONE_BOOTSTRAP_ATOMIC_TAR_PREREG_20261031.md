# Phone bootstrap transactional tar extraction — prereg 2026-10-31

Owner GPT-6; independent review-only child of Run98 #1465 exact verified parent `bc80a0d7df7031f5c18a11531969f5fc482b5891`. No changes to Run98 source ZIP, original artifacts, pinned models, seeds, cohorts, native runner, learning/age policy or frozen SourceHandoff Runtime.

## Problem and proposed test before code
Current `v13/bootstrap.py:extract` uses `tarfile.extractall` with the data filter only if Python exposes `tarfile.data_filter`; Python 3.10/11 compatibility and symlink descendants require an explicit archive-member check. It extracts directly into a possibly existing installation tree, so malformed or interrupted extraction may leave partial files. Install-native calls it for pinned llama.cpp release/source tarballs. This is a **software integrity/resume** task, not a model or utility experiment.

Proposed implementation: separate stdlib-only `v13/safe_tar.py`, retain the `bootstrap.extract` callable; stage files and directories before creating in-tree symlinks, reject traversal, duplicate normalized paths, hardlinks/devices, symlink-parent writes and destination symlinks, then same-filesystem replace with rollback on failure. On retry, a fully validated tree replaces a prior extracted tree. Hash provenance stays the responsibility of the existing pinned `download_file`.

Predeclared checks: real bootstrap import; crafted valid tar with internal link; retry replacement; traversal refusal; external link refusal; nested member below link refusal; hardlink refusal; normalized duplicate refusal; pre-existing destination symlink refusal; file/dir collision preserving old extraction. Run locally and on a fresh Linux GitHub Actions runner, with no model download. Privacy scan and compile check. Preserve all failures and negative gates. Do not claim Termux/Redmi proof or native execution.

Expected stop/continuation: after a remote verified test/checkpoint, inspect actual failure/resume paths and continue next independent authorized package; no merge or gate promotion.
