# Independent Linux API review (2026-10-25)

Primary sources reviewed:
- https://www.man7.org/linux/man-pages/man2/pidfd_send_signal.2.html — pidfd is a stable process reference; signalling by recycled numeric PID can affect an unrelated process; a dead pidfd target returns ESRCH.
- https://www.man7.org/linux/man-pages/man2/pidfd_open.2.html — pidfd_open guarantees and limitations, including child zombie identity.
- https://cdn.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html — cgroup.kill kills cgroup and descendant cgroups, with concurrent forks handled; requires owned writable cgroup.
- Frozen local Run21 patch `v13/code/docs/coordination/LP3_RUN21_POSTREAP_REVIEW.patch` — post-reap `_cleanup_owned_group` must probe, not signal numeric PGID.

Review outcome: revised synthetic test may probe `killpg(pgid,0)` but must reject any nonzero signal after reaping. It checks failure, no receipt, residue, poisoned lock, and uses pidfd for cleanup of its own known fixture. This does **not** establish real cgroup containment, and does not change LP3's blocked native acceptance gate.

Remaining limitation: pidfd_open on a grandchild PID obtained after the leader has exited is not an atomic ownership acquisition; the test's short-lived fixture has a bounded race before pidfd_open. Do not treat this as a production cleanup strategy. Real LP3 requires atomic cgroup creation/ownership (Run24 candidate) and independent delegated-host proof.
