# Run178 — pidfd child-ownership independent review (2026-10-25)

Base: Run177 `d2c8deb63591c64c2ee8c2579204017ebdc7e7cc`. Ownership: **new** `scripts/run178_pidfd_child_ownership.py`, `tests/test_run178_pidfd_child_ownership.py`, this proof and focused workflow only. No changes to frozen Runtime, Run175 candidate, registered native cohorts, models, age/learning permissions or Canon. Branch-scoped candidate, not production integration.

## Review finding and bounded fix

Run175 discovers a PID by parsing `/proc/<pid>/status` `PPid`, then calls `os.pidfd_open(pid, 0)` and immediately `pidfd_send_signal`. A pidfd pins the process identity **after** it is opened; it does not prove that the PID still belongs to the subreaper at open time. A stale or adversarially wrong `/proc` candidate can cause an unrelated signal. The dedicated-childless-controller precondition reduces but does not logically close the check/open gap.

Run178 independently adds `open_owned_child_pidfd`: after `pidfd_open`, call `waitid(P_PIDFD, fd, WEXITED|WNOHANG|WNOWAIT)`. A non-child raises `ECHILD`/`ChildProcessError`; no signal is attempted, the fd is closed, and the candidate is rejected. `WNOWAIT` leaves an exited child's wait status available for the existing reaper. Other failures propagate fail-closed. Caller must close returned fd. No numeric PID kill or process-group fallback. This proves a **narrow Linux process ownership guard**, not complete cgroup isolation, stable process-tree enumeration or crash cleanup. It does not authorize using Run175 as a replacement for Run24 `clone3(CLONE_INTO_CGROUP)`.

Primary source: Linux man-pages `waitid(2)` (P_PIDFD, WNOWAIT and ECHILD), `pidfd_open(2)` (PID reuse conditions): https://man7.org/linux/man-pages/man2/wait.2.html and https://man7.org/linux/man-pages/man2/pidfd_open.2.html (checked 2026-10-25). This is a Linux-native synthetic process experiment, not model inference.

## Observed checks

`python -m compileall -q v13/code/scripts/run178_pidfd_child_ownership.py v13/code/tests/test_run178_pidfd_child_ownership.py`: PASS.

`python -m unittest discover -s v13/code/tests -p 'test_run178_pidfd_child_ownership.py' -v`: **5/5 PASS**, local Linux kernel 6.18.55, Python 3.13.5. Checks: own child accepted and pidfd-killed/reaped; unrelated live grandchild rejected and left alive; bad PID rejected; synthetic ECHILD refused; no numeric-signal fallback. `native_synthetic_evidence.json` binds the SHA-256 of code, tests and closed `test_raw.log` (raw log also archived). No cgroup write access on this host.

Original Run173 full suite remains **FAIL** (one live orphan and optional fixture permission ERROR); Run176 separate portability candidate is not an LP3 proof. Run174 real B1 heldout and Run177 B2 identity are separate owners, not modified here.

## Gates and next step

`STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. No new acceptance promotion.

Next: independent review of the guard and its test in CI; only then propose integrating ownership check into a dedicated subreaper controller **alongside** (never instead of) atomic cgroup placement. Test races, unrelated children, controller crash and original Run173 descendant regression. The original cgroup-v2 kernel/Redmi/model gates remain untouched. Do not use rejected anyone-writable Drive backup.
