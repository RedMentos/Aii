# LP3 Run18 — independent orphan-process-group review (2026-10-24)

Base: PR #53, commit `2c009f322b8613e2f09025759c1d0269423aa252`; exact Run17 launcher blob `5cdc15957f6e4e260d5362924e918bdf6b6cd5f2`. Scope owned: only isolated LP3 serial-cohort candidate patch, new adversarial test and Run18 proof/coordination files. No production runtime, original preregistration, Canon, ROADMAP or other owner's code changed.

**Confirmed RED:** A synthetic launcher child spawns a sleeping descendant and exits 0. Run17 treats its direct-child `Popen.wait()` as proof the process group is gone; it emits `LOCAL_CLOSED_EVIDENCE_UNPUBLISHED_ANCHOR` and releases the lock with descendant still running. Original failing trace is preserved at `docs/proofs/continuation-20261024/lp3-run18/run18_red.log`.

**Candidate fix:** after direct-child wait, check the group created by `start_new_session=True`; if any member remains, send bounded TERM/KILL to that owned group, reject success/receipt, and record group status. If group absence is not established, poison the host-local lock file to block future attempts, including attempts with different output directories, pending explicit operator inspection. Never signal other owners' processes. New tests reproduce both false-success and persistent-poison refusal.

**Verification:** `PYTHONPATH=v13/code/scripts:v13/code/tests python -m unittest discover -s v13/code/tests -p 'test_lp3*.py'` on the assembled Run14+15+16+17 source plus Run18 patch: 146/146 software/synthetic PASS (includes inherited duplicate tests; 2 unique new adversarial cases). `compileall` PASS. Patch applied cleanly to exact Run17 source; patched launcher Git blob `7c3719a31826e562ecf83816d97c67e203866948`. No native inference. Full checkout/full suite/official privacy scan NOT RUN due GitHub DNS failure.

**Current host:** cgroup memory 4294967296 bytes; pinned HF master seven assets absent; LP2 and LoRA fixtures absent; `transformers` absent; local LP3 process count 0 only; global job owner and RAM fit NOT VERIFIED. No Redmi measurement.

**Original gates unchanged:** STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, `canonical_architecture_complete=false`, `user_full_scope_complete=false`. A local test cannot demonstrate JEPA or AGI.

**Primary technical references (checked 2026-10-24):** Python `subprocess` docs, https://docs.python.org/3/library/subprocess.html ; Linux `killpg(3)`, https://man7.org/linux/man-pages/man2/killpg.2.html . Group signalling may treat zombies conservatively; a descendant can escape into another session; direct SIGTERM of wrapper before cleanup remains open. These are NOT solved by the patch.

**Next exact step:** independently review this patch; integrate in complete latest checkout only after checking newer Claude owner work; run full suite and official privacy scanner; add bounded direct-SIGTERM and escaped-group counterexamples; verify native assets, global owner, RAM fit; then run preregistered serial LP3 four-seed native cohort and externally publish closed raw evidence. Do not retry the 2026-10-24 rejected anyone-writable Drive backup.
