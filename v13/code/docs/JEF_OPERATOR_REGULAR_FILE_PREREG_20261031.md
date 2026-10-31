# JEF operator regular-file-only bounded input — preregistration (2026-10-31 UTC)

Owner: GPT-6 scheduled continuation. Review-only child of PR #1412 exact parent `77dd7775c63571dec90fa1291424dd541a6d2d71`. This preregistration is committed and read back before code/tests. Canon, original registered native cohorts, models, seeds, scorers and RED evidence unchanged.

## Threat and scope
The previous bounded 16 KiB `Path.open("rb")` read can block indefinitely on a FIFO or similar special path before opening Runtime. The opt-in local diagnostic is not intended to read device nodes, pipes, sockets, directories, or symlink redirects. Use a single OS-level `O_RDONLY | O_NONBLOCK | O_NOFOLLOW` open and `fstat` regular-file check, then read at most MAX_INPUT_BYTES+1 from that already-open descriptor, close it on all outcomes, and preserve strict JSON grammar and SHA of exactly accepted bytes. Require Linux/Android `O_NOFOLLOW`; fail closed if unavailable. Do not call Runtime on invalid input. This is a local operator safety boundary, not a sandbox against hostile same-user filesystem mutation.

## Prospective software acceptance
- Existing 52 focused methods still pass unchanged; no native model invoked.
- Real FIFO (without writer) returns INPUT_RED within a short subprocess timeout; Runtime home remains absent.
- Directory, symlink to valid regular JSON, empty, oversize, duplicate JSON keys and invalid UTF-8 remain INPUT_RED; a direct regular-file fixture retains successful source-bound SHADOW DRAFT and C6 read-only challenge.
- Injected `os.open` error and descriptor validation failure do not leak file descriptors.
- No real TTY approval, visible output, FINAL, tools, learning or production Runtime wiring. Negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, Redmi unmeasured.

## Verification
Pin changed blobs and Canon in branch-specific GitHub Actions. Preserve terminal run and closed raw artifact even if RED; verify ZIP SHA256, CRC, inner SHA256SUMS, and permitted private Library byte-identical backup. No live Redmi claim from Linux software tests.
