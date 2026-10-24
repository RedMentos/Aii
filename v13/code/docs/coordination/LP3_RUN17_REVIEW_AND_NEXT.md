# LP3 Run17 — independent serial launcher lifecycle review (2026-10-24)

**Base:** PR #52 `58d8fbd4da846621c730247ac188bae20676b860`; stacked on Claude PR #38. The Run16 launcher remains a bundled candidate, not an installed runtime module. This review preserves the complete V13 Canon and all user decisions.

**Owned files (sequential, no live subagents claimed):** Run17 implementer owned `scripts/lp3_serial_cohort.py`; adversarial reviewer owned `tests/test_lp3_serial_cohort.py`; checkpoint coordinator owned only new Run17 docs/proofs. No heavy native job or foreign runtime edit.

**Three reproduced failures (before patch):** an interrupted `Popen.wait` left the owned child running after the local lock was released; SIGKILL escalation used an unbounded final `wait()`; native stdout/stderr digests used unbounded `read_bytes()` (both success and failure paths). The counterexamples are preserved in `lp3-run17/RAW_TESTS.txt` and exact local logs in the downloadable ZIP.

**Changes:** interruption cleanup sends TERM then KILL to only the owned child process group and waits with bounds; final post-KILL wait bounded; native log SHA-256 streamed in 1 MiB chunks; failure status retains log hash. Cleanup failure is still recorded and requires operator inspection. This does not guarantee reaping an uninterruptible D-state process or prevent repeated-signal races; global ownership remains external.

**Verification:** Original Run16 bundle reconstructed from user-provided archive and earlier LP3 deltas in chronological order. Four Git blobs checked against current remote: readiness `2dfa7099`, evidence auditor `6068ddaf`, candidate `4006a461`, readiness test `beee1b9e`. Baseline **102/102 PASS**. Three deliberately failing adversarial tests then corrected; final **105/105 LP3 software/synthetic PASS**, `compileall` PASS. `git apply` on pristine Run16 source reproduced the two final Git blobs:
- launcher `5cdc15957f6e4e260d5362924e918bdf6b6cd5f2` (SHA-256 `159d9bf680003a6f934a58c669dacc9ad78c2852be7ec4310c3aa60436475af8`)
- tests `58bbe101abe59cdfea9c3a295c6bad7a98e2c60c` (SHA-256 `83e9030555d1c5bc51179a7922127604e8ed7f5c245a2970d7127460c999ba5f`).

**Local direct native readiness:** BLOCKED; cgroup 4,294,967,296 bytes, pinned HF snapshot seven files absent, two fixtures absent, `transformers` absent, local LP3 processes observed 0; global owner and actual memory fit not proven. No native model/Redmi execution. Full checkout/full suite/official privacy scan NOT RUN because container cannot resolve github.com; isolated LP3-focused suite only. Scoped manual review finds no secrets or user data in Run17 patch.

**Evidence grades / unchanged gates:** STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full V13 `INCOMPLETE`; no promoted native claims. `native_executed=false` in synthetic status is deliberately not treated as model proof.

**Primary source (accessed 2026-10-24):** Python subprocess docs https://docs.python.org/3/library/subprocess.html: timeout does not kill a child automatically and `wait(timeout)` can raise `TimeoutExpired`. Python os docs https://docs.python.org/3/library/os.html: `killpg` targets a process group. No third-party code copied.

**Exact next:** independently apply `LP3_RUN17_LIFECYCLE_REVIEW.patch` to the two files from PR #52's `SOURCE_AND_TESTS.tar.xz` after checking remote hashes, install in a complete current checkout only after owner review; full suite and official privacy scan; recheck assets/host/process ownership and RAM; execute the unchanged registered four-seed cohort serially; independently publish closed receipt SHA; then equal-budget generated-answer ablation.

**Backup constraint:** rejected anyone-writable Drive destination not retried. User decision required: none.
