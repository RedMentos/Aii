"""Independent Run178 Linux pidfd ownership guard, NOT LP3 integration.

A pidfd stabilizes the identity found by pidfd_open, but does not establish
that a PID scraped from /proc still refers to an owned child. Validate the
opened *descriptor* with waitid(P_PIDFD, WNOWAIT) before any signal.
Only use inside a dedicated, childless-at-start subreaper controller.
"""
import os
import sys


class UnownedProcess(RuntimeError):
    """The opened process is not waitable by this controller."""


def open_owned_child_pidfd(pid):
    """Return a pidfd for a current child, or fail closed without signalling.

    The caller owns the returned fd and must close it. WNOWAIT deliberately
    does not consume an exited child's status. No numeric PID signalling or
    post-reap process-group fallback is permitted.
    """
    if sys.platform != 'linux' or not all((hasattr(os, 'pidfd_open'),
                                             hasattr(os, 'P_PIDFD'),
                                             hasattr(os, 'WNOWAIT'))):
        raise RuntimeError('requires_linux_pidfd_waitid')
    if type(pid) is not int or pid <= 0:
        raise ValueError('positive_integer_pid_required')
    fd = os.pidfd_open(pid, 0)
    try:
        try:
            os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError as exc:
            raise UnownedProcess('pidfd_not_waitable_child') from exc
    except BaseException:
        os.close(fd)
        raise
    return fd
