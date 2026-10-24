# LP3 Run23 — bounded basic clone3 host probe

Linux host kernel `6.18.55`, `Seccomp: 0` from `/proc/self/status`. Compiled `clone3_capability_probe.c` with `gcc -Wall -Wextra -O2` and ran a **single no-cgroup** `clone3` child, reaped with `waitpid`: `clone3_basic=AVAILABLE child_exit=0`. Raw output: `clone3_probe.log`.

SHA-256: C source `3db3fc27bb67447e61f15013f360eafd762de5d1dec24bb6f632e7b123c1c037`, raw log `338f54221d778ccd3ed4bb1b4dd49138adcf4b815b62966e0ca2e38f912c21d0`.

**Claim limit:** Basic syscall availability is NOT `CLONE_INTO_CGROUP` availability or correct cgroup delegation. No private writable cgroup exists on this host, so no `CLONE_INTO_CGROUP`, detached `setsid`, crash recovery or native LP3 test was run. Do not use the root cgroup or signal unrelated processes. A future isolated atomic-spawn implementation must verify ownership, cgroup fd and kernel permission, then demonstrate fork/setsid containment with bounded cleanup on a delegated host. Original V13 negative gates unchanged.

Primary: https://man7.org/linux/man-pages/man2/clone.2.html ; https://docs.kernel.org/admin-guide/cgroup-v2.html .
