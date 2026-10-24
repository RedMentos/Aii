# V13 / Inquisition-JEPA — Run24 atomic clone3 bootstrap candidate (2026-10-24)

**Remote base:** PR #59 `881ae61e7f5b3a2ea62bbc18305b0e30d01ee001` (stacked on Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`). **Work branch:** `codex/lp3-atomic-clone3-20261024`.

## Scope and ownership

New isolated source only: `scripts/lp3_atomic_clone3.c`, `scripts/lp3_atomic_bootstrap.py`, `tests/test_lp3_run24_atomic_clone3.py`; new closed logs/state/manifest. No edits to Canon, original preregistration, native runner, original STEP2/B3 gates, runtime, or other owners' files. This code is **OFF by default and not wired into `lp3_serial_cohort.py`**. It does not replace the original Python cgroup join path, which remains unproven against ELF prejoin code. No native LP3 attempt was launched.

## Implemented

- A **static Linux C helper** uses `clone3(CLONE_INTO_CGROUP|CLONE_PIDFD)` to request kernel-atomic placement of the candidate child into the fresh owned `lp3-active` cgroup. There is **no fallback** to fork + cgroup.procs. Child remains blocked on a private socket until the parent confirms its PID in the owned `cgroup.procs`, writes and fsyncs a closed-schema marker, and releases it to `execve` the absolute original command with inherited environment. The child calls `setsid()` **inside** its assigned cgroup.
- Parent supervises with `waitpid`, handles SIGTERM/SIGINT, and signals the owned child via **pidfd**, not a recycled numeric PID. Bounded abort attempts fail closed; global ownership and cgroup subtree cleanup remain the external coordinator's responsibility.
- A Python staging adapter validates an explicit SHA256 of the reviewed static ELF64 ET_EXEC, rejects PT_INTERP/PT_DYNAMIC and wrong architecture, snapshots it into a sealed memfd to avoid check/exec file replacement, prepares absolute launch args, and validates the exact marker schema/identities. This is a *staging adapter*, not a complete LP3 lifecycle integration.

## Evidence (graded)

- **Linux native, no cgroup:** static helper compiled with gcc 14.2; readelf found no INTERP/DYNAMIC; a sealed memfd launched the real helper with a private *non-cgroup* directory, and it rejected the attempt (exit 125), creating neither marker nor native sentinel. An `LD_PRELOAD` constructor fired in the dynamic negative control but **did not** fire in the static helper. This is a real Linux ELF/loader negative control, **not** a positive kernel cgroup test.
- **Software/synthetic:** 11/11 new targeted tests PASS; 166/166 assembled LP3 tests PASS; compileall PASS. Previous Run23 SIGTERM flake was not reproduced in 12 corrected isolated reruns, but remains unresolved and must not be declared fixed.
- **Kernel capability:** basic `clone3` (without `CLONE_INTO_CGROUP`) AVAILABLE and reaped one child. `CLONE_INTO_CGROUP`, writable delegation, detached-session containment, crash/stale-slot recovery and cross-host ownership are **NOT RUN / UNVERIFIED**.
- **Full repository/Redmi:** NOT RUN. Current host cgroup2 mounted read-only, memory.max 4 GiB, seven registered HF assets, two fixtures and transformers absent. No native model measurements.

## Build and reproduce

Use Linux with gcc, never the cgroup root and never an unowned cgroup:

```sh
cd v13/code
# Build the staged helper, not an installed production component.
gcc -std=c11 -O2 -Wall -Wextra -Werror -static -no-pie \
  -o /tmp/lp3_atomic_clone3 scripts/lp3_atomic_clone3.c
PYTHONPATH=scripts:tests python -m unittest tests.test_lp3_run24_atomic_clone3 -v
PYTHONPATH=scripts:tests python -m unittest discover -s tests -p 'test_lp3*.py' -q
```

Do **not** call the native runner with this helper yet: its integration into the serial launcher, operator-delegated writable cgroup, real kernel negative control and receipt lifecycle are still pending. The helper's successful cgroup behavior is **not claimed**.

## Primary sources (checked 2026-10-24)

- Linux `clone3` `CLONE_INTO_CGROUP` semantics and permission/error cases: https://man7.org/linux/man-pages/man2/clone.2.html
- Linux kernel cgroup v2 delegation, `cgroup.procs`, `cgroup.events` and `cgroup.kill`: https://docs.kernel.org/admin-guide/cgroup-v2.html
- Linux `pidfd_send_signal`: https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html
- ELF program headers: https://refspecs.linuxfoundation.org/elf/gabi4+/ch5.pheader.html

## Gates / next step

STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; `canonical_architecture_complete=false`; `user_full_scope_complete=false`.

**Exact next step:** Independent full-checkout source/privacy review and C-helper audit. On a Linux host with an operator-delegated writable cgroup v2, run the bounded synthetic `setsid()` child + detached grandchild test using this helper; verify marker, no prejoin sentinel, cgroup residue detection/kill, SIGTERM, SIGKILL, stale-slot behavior. Only after positive kernel evidence, hash-bind and integrate the helper into the isolated LP3 serial launcher, update its receipt to distinguish `helper_pid`/`child_pid`, and rerun complete tests. Then recheck pinned native prerequisites, global job ownership and measured RAM; only then execute the unchanged preregistered four-seed LP3 cohort and separate generated-answer utility ablation. Do not claim V13 completion or AGI.

No rejected anyone-writable Drive backup destination was used.