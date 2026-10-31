# Pinned llama.cpp b10964 archive compatibility — prereg 2026-10-31

Owner GPT-6; independent review-only child of phone bootstrap PR #1469 exact parent `3d411865554a82e267796277cc4d03f09be628a7`. Existing Run98 source ZIP, prior software Actions 41206579353/41206665368 and private originals are immutable. No changes to pinned b10964 catalog SHA/size/URL, model cohorts, runtime, age, learning or native ownership.

## Registered question
Does the newly staged `bootstrap.extract` accept both **actual original pinned** b10964 source archive and Linux-x86_64 binary archive without dropping required files, while preserving the same installed-tree bytes after an extraction retry? Previous tests used only synthetic tar members and do not prove compatibility with real upstream bytes.

Fixed sources from `v13/code/specs/models.json`: runner tag b10964, source URL `https://github.com/ggml-org/llama.cpp/archive/refs/tags/b10964.tar.gz`, size 37420323, SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`; Linux-x86_64 prebuilt size 16825086, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Source revision b29c606e2 as recorded by catalog. Do not change these.

## Predeclared method and acceptance
On isolated Linux Actions, use existing `models.download_file` to download+SHA/size validate exactly those two public source artifacts. Invoke the real `bootstrap.extract` on both into fresh temp dirs; assert source `llama.cpp-b10964/CMakeLists.txt` and exactly one regular `llama-server` binary with ELF magic. Hash each extracted regular file's path/content deterministically, re-extract the identical original archive into same destination, assert byte-for-byte tree fingerprint parity. Preserve raw stage logs, hashes, manifest counts, symlink counts, exit receipts, exact HEAD, and ZIP SHA256SUMS even if RED. No model files, native binary execution, model training, or Redmi claims. Linux software compatibility is not native/Redmi proof.

Next after original ZIP audit: if RED, preserve and diagnose without silently altering pins; if GREEN, checkpoint then continue the actual phone install failure/resume or another independent Canon organ. No gate promotion.
