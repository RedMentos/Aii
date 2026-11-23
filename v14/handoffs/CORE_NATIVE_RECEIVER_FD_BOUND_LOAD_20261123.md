# Core handoff — descriptor-pinned native receiver load (2026-11-23)

## Product defect

The diagnostic native receiver verified the receiver GGUF by pathname, then launched a child process that reopened the same pathname. A concurrent rename/replacement between the hash and llama.cpp's `llama_model_load_from_file()` could therefore make the child load different bytes from those verified by the approval and probe wrapper.

## Change on this branch

- `v13/code/v13/native_latent_receiver.py` opens the receiver model beneath the canonical `home/models` root by descriptor-relative, no-follow traversal.
- The final descriptor must be a non-empty regular file; FIFO opens are nonblocking and rejected.
- SHA-256 and stable device/inode/size/mtime/ctime are verified on the open descriptor.
- The native child receives that exact descriptor through `subprocess.Popen(pass_fds=...)` and loads `/proc/self/fd/N`, not the mutable original pathname. Post-load verification re-hashes the descriptor; rename-only ctime changes are tolerated while device/inode/size/mtime and bytes remain stable, whereas in-place changes are rejected.
- The descriptor remains open through native completion and its hash/identity are rechecked before accepting the receipt.
- The staged receiver overlay's source SHA-256 pin is refreshed; the new tests are in the existing native receiver workflow path.

## Evidence boundary

- LOCAL_LINUX_ISOLATED: CPython 3.13.5 exact-helper reproduction passed descriptor inheritance across atomic pathname replacement; the child read the verified original SHA-256. Nonblocking FIFO rejection and post-open in-place mutation detection passed. `py_compile` passed for the isolated harness.

- LOCAL_LINUX primitive check: POSIX child inherited an open model descriptor, the pathname was atomically replaced before the child opened `/proc/self/fd/N`, and the child still read the original bytes.
- Full Aii checkout tests: NOT_RUN here because GitHub DNS is unavailable and no checkout is mounted. Exact-source GitHub CI is required.
- Native llama.cpp model execution: NOT_RUN locally; this environment has no Aii checkout or installed GGUF/native receiver.
- TERMUX/REDMI: REDMI_UNVERIFIED. No private relay query, native probe, update request, model/weight/permission change or device mutation was performed.
- Production B3 remains OFF. This closes a file-path TOCTOU for the diagnostic receiver; it does not prove trained latent alignment, semantic utility or production coupling.

## Next

Run the exact QA-base native receiver workflow on this branch, inspect all exact-head checks, then coordinate with QA #2377 and Core stage PR #2385. Keep the probe diagnostic-only until a separate explicit device decision and held-out utility/parity/zero/shuffle/OOD controls.
