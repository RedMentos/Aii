"""Source-bound native cancellation proof, without granting runtime/learning authority.

The native runner's interrupted child must be reaped. A different resident role
may legitimately remain alive; treating *all* pool PIDs as the cancelled child
creates a false-negative when body residency is enabled.

This helper never infers reaping from the runner's claim alone: it also checks
the exact interrupted PID against the pool and the OS. Unknown evidence fails
closed. Historical acceptance reports and gates are not rewritten.
"""
import os


def pid_alive(pid):
    """Conservative POSIX liveness probe: permission/unknown means still alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def cancelled_native_process_stopped(runner_metrics, pool_pids, *, probe=pid_alive):
    """Prove the *cancelled* native child is reaped, not that the pool is empty.

    `probe(pid)` returns True for a live/unknown PID, False only for an
    independently observed absent PID. The optional probe supports software
    counterexamples; actual integration always uses the OS probe.
    """
    if not isinstance(runner_metrics, dict) or runner_metrics.get("status") != "CANCELLED":
        return False
    release = runner_metrics.get("interruption_unload")
    if not isinstance(release, dict) or release.get("process_reaped") is not True:
        return False
    before = release.get("before")
    if not isinstance(before, dict):
        return False
    pid = before.get("pid")
    if type(pid) is not int or pid <= 0:
        return False
    if not isinstance(pool_pids, (list, tuple, set)):
        return False
    if any(type(p) is not int or p <= 0 for p in pool_pids):
        return False
    if pid in pool_pids:
        return False
    try:
        return probe(pid) is False
    except Exception:
        return False
