# LP3 Run19 — SIGTERM lifecycle review and detached-session counterexample (2026-10-24)

**Base:** PR #54 head `aace36e7d1b4ffc6d4ad2eff951a8ace7a51f6ae`; exact source blob `7c3719a31826e562ecf83816d97c67e203866948`. The Run19 candidate blob is `394deb439b1305534dcb3f51c916a0250f79c4c1`. No frozen runtime, preregistered LP3 runner, Canon, ROADMAP, Claude-owned files or gates were modified.

**Owned files:** isolated patch + regression test in `docs/proofs/continuation-20261024/lp3-run19/LP3_RUN19_CODE_ONLY.tar.xz.base64`, scoped BUILD_STATE and raw proof files. Decode using `base64 -d LP3_RUN19_CODE_ONLY.tar.xz.base64 | tar -xJf -` in a trusted scratch checkout. This is NOT installed at `scripts/` and must not be merged without independent review. Source can be reconstructed by applying the patch to the exact Run18 launcher blob. Code-only tar.xz SHA-256: `4c5b3314363128c2b284335e15ad25ea0a1614ea0bd04506caf971214d4e1cef`.

## Confirmed findings

**RED reproduced:** direct SIGTERM to the wrapper during its own running child killed the wrapper, leaving the child alive. `run19_red.log` is preserved. **Candidate fix:** main-thread SIGTERM handler installed before `Popen`, signal deferred during spawn until process handle assigned (no blocked SIGTERM inherited by child), protected arm inside the cleanup try, bounded owned-child/group cleanup, repeated signals cannot interrupt cleanup, signal during group cleanup blocks receipt, original handler restored. **GREEN:** 5/5 new Linux/synthetic tests PASS; `compileall` PASS. This is not native HF/Redmi evidence.

**Additional RED, unresolved:** a synthetic child launches a detached new-session descendant then exits. The launcher publishes `LOCAL_CLOSED_EVIDENCE_UNPUBLISHED_ANCHOR` and a receipt while that descendant is still alive. `run19_detached_red.log` records this **FAIL-OPEN**; the diagnostic terminated only its own child. Run19 SIGTERM fix does NOT solve escaped-session containment. Do not use this wrapper as proof of complete descendant isolation.

**Broader LP3 suite:** 151 tests executed, 1 inherited 2-second synthetic child timeout failure; a rerun had a different inherited timeout failure. Both runs are NOT PASS; preserve failure logs, do not round to 151/151. Complete repository suite and official privacy scanner NOT RUN (full checkout unavailable due github.com DNS failure).

**Current host readiness (rechecked):** 4 GiB cgroup, all seven pinned HF model assets absent, LP2/LoRA fixture sources absent, `transformers` absent, local LP3 process scan zero at that instant only. Global owner and actual native RAM fit unverified. No native four-seed LP3, no Redmi measurement.

**Original gates unchanged:** STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, `canonical_architecture_complete=false`, `user_full_scope_complete=false`. No AGI/full completion claim.

**Primary sources checked 2026-10-24:** Python signal docs https://docs.python.org/3/library/signal.html (main-thread signal delivery, asynchronous exceptions); Python subprocess docs https://docs.python.org/3/library/subprocess.html (`start_new_session` uses `setsid`); Linux killpg https://man7.org/linux/man-pages/man2/killpg.2.html (process-group signalling). SIGKILL, interpreter crashes, process-group escape and arbitrary detached descendants remain outside this patch's guarantee.

**Next exact step:** independently review the Run19 patch against the latest full checkout and newer Claude owner work; resolve detached-session fail-open with independently proven job/cgroup isolation or equivalent; run full suite and official privacy scanner; recheck model assets, global owner and RAM fit; only then launch the unchanged preregistered four-seed LP3 native cohort with externally anchored raw evidence. Do not retry the rejected anyone-writable Drive backup.
