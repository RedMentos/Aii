/*
 * V13 LP3 / isolated OFF-by-default atomic child placement candidate.
 *
 * A reviewed, statically linked helper is launched by the trusted LP3
 * coordinator. Its CHILD is born in an operator-owned cgroup-v2 subtree
 * using clone3(CLONE_INTO_CGROUP|CLONE_PIDFD), BEFORE it can run any user
 * executable/ELF loader. No fallback to fork, clone or cgroup.procs writes.
 *
 * This is lifecycle containment, not a security sandbox: a privileged
 * process can migrate out of its cgroup. Requires a real delegated cgroup
 * kernel test before any native LP3 use or containment PASS claim.
 *
 * Build (Linux x86_64 or aarch64):
 * gcc -std=c11 -O2 -Wall -Wextra -Werror -static -no-pie \
 *     -o lp3_atomic_clone3 lp3_atomic_clone3.c
 *
 * Usage: lp3_atomic_clone3 ABS_CGROUP ABS_MARKER -- ABS_COMMAND [ARGS...]
 * The helper writes a marker ONLY after kernel-verified child membership,
 * then releases the child to execve with its inherited, unchanged environ.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef SYS_clone3
#error "Linux clone3 syscall number is required"
#endif
#ifndef SYS_pidfd_send_signal
#error "Linux pidfd_send_signal syscall number is required"
#endif
#ifndef CLONE_INTO_CGROUP
#error "Linux headers with CLONE_INTO_CGROUP are required"
#endif

#define BLOCKED 125
#define CHILD_EXEC_FAILURE 127
#define MAX_GROUP_PATH 2048
extern char **environ;
static volatile sig_atomic_t stop_requested = 0;

static void handle_stop(int signo) { stop_requested = signo; }
static void fail(const char *message) {
    fprintf(stderr, "LP3_ATOMIC_BLOCKED: %s (errno=%d)\n", message, errno);
}
static int absolute(const char *path) { return path && path[0] == '/'; }
static int owned_group_name(const char *path) {
    size_t n = strlen(path);
    static const char suffix[] = "/lp3-active";
    /* Require at least one delegated component between cgroup root and slot. */
    return n > 15 + sizeof(suffix) - 1 &&
        strcmp(path + n - (sizeof(suffix) - 1), suffix) == 0 &&
        strncmp(path, "/sys/fs/cgroup/", 15) == 0;
}
static int open_owned_group(const char *path) {
    struct statfs fs;
    if (!absolute(path) || strlen(path) >= MAX_GROUP_PATH ||
        !owned_group_name(path)) {
        errno = EINVAL;
        return -1;
    }
    /* realpath(path, caller_buffer) assumes PATH_MAX bytes; a 2048-byte
       stack buffer is not sufficient on all supported Linux hosts. */
    char *canonical = realpath(path, NULL);
    if (!canonical) return -1;
    int matches = strcmp(path, canonical) == 0;
    free(canonical);
    if (!matches) {
        errno = EINVAL;
        return -1;
    }
    int fd = open(path, O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) != 0 || (unsigned long)fs.f_type != CGROUP2_SUPER_MAGIC) {
        close(fd);
        errno = EINVAL;
        return -1;
    }
    return fd;
}
static int child_in_group(int groupfd, pid_t child) {
    int fd = openat(groupfd, "cgroup.procs", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return 0;
    FILE *stream = fdopen(fd, "r");
    if (!stream) { close(fd); return 0; }
    long value;
    int found = 0;
    while (fscanf(stream, "%ld", &value) == 1) {
        if (value == (long)child) { found = 1; break; }
    }
    fclose(stream);
    return found;
}
static int write_marker(const char *path, const char *group, pid_t child) {
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    /* The canonical cgroup path is restricted to ordinary /sys/fs/cgroup
       components; reject quotes/backslashes so JSON remains unambiguous. */
    for (const char *p = group; *p; ++p) {
        if (*p == '"' || *p == '\\' || (unsigned char)*p < 0x20) {
            close(fd); errno = EINVAL; return -1;
        }
    }
    char json[MAX_GROUP_PATH + 256];
    int n = snprintf(json, sizeof(json),
        "{\"schema\":\"V13_LP3_ATOMIC_CLONE3_V1\",\"cgroup\":\"%s\","
        "\"helper_pid\":%ld,\"child_pid\":%ld,\"atomic_placement\":true,"
        "\"pidfd\":true,\"verified_membership\":true}\n",
        group, (long)getpid(), (long)child);
    if (n < 0 || (size_t)n >= sizeof(json)) { close(fd); errno = E2BIG; return -1; }
    ssize_t written = write(fd, json, (size_t)n);
    int ok = (written == n && fsync(fd) == 0);
    int saved = errno;
    close(fd);
    if (!ok) { errno = saved ? saved : EIO; return -1; }
    return 0;
}
static void send_pidfd(int pidfd, int sig) {
    if (pidfd >= 0) (void)syscall(SYS_pidfd_send_signal, pidfd, sig, NULL, 0);
}
static int wait_bounded(pid_t pid, int pidfd, int *status) {
    /* Only used on abort/interrupt. Never send signals by numeric PID. */
    send_pidfd(pidfd, SIGTERM);
    for (int phase = 0; phase < 2; ++phase) {
        for (int i = 0; i < 40; ++i) {
            pid_t w = waitpid(pid, status, WNOHANG);
            if (w == pid || (w < 0 && errno == ECHILD)) return 0;
            if (w < 0 && errno != EINTR) return -1;
            struct timespec pause = {.tv_sec = 0, .tv_nsec = 50000000L};
            nanosleep(&pause, NULL);
        }
        send_pidfd(pidfd, SIGKILL);
    }
    return -1; /* coordinator must use owned cgroup.kill; never claim empty */
}
int main(int argc, char **argv) {
    if (argc < 5 || strcmp(argv[3], "--") != 0 ||
        !absolute(argv[1]) || !absolute(argv[2]) || !absolute(argv[4])) {
        fprintf(stderr, "usage: lp3_atomic_clone3 CGROUP MARKER -- ABS_COMMAND [ARGS...]\n");
        return BLOCKED;
    }
    int groupfd = open_owned_group(argv[1]);
    if (groupfd < 0) { fail("not an owned canonical cgroup-v2 subtree"); return BLOCKED; }
    struct stat st;
    if (lstat(argv[2], &st) == 0 || errno != ENOENT) {
        fail("marker already exists or cannot be checked"); close(groupfd); return BLOCKED;
    }
    int gate[2];
    if (socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, gate) != 0) {
        fail("gate socketpair"); close(groupfd); return BLOCKED;
    }
    struct sigaction action = {.sa_handler = handle_stop};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, NULL) || sigaction(SIGINT, &action, NULL)) {
        fail("signal handler"); close(gate[0]); close(gate[1]); close(groupfd); return BLOCKED;
    }
    if (stop_requested) {
        fail("interrupted before clone3; no child created");
        close(gate[0]); close(gate[1]); close(groupfd); return BLOCKED;
    }
    int pidfd = -1;
    struct clone_args args = {0};
    args.flags = CLONE_INTO_CGROUP | CLONE_PIDFD;
    args.cgroup = (uint64_t)groupfd;
    args.pidfd = (uint64_t)(uintptr_t)&pidfd;
    args.exit_signal = SIGCHLD;
    pid_t pid = (pid_t)syscall(SYS_clone3, &args, sizeof(args));
    if (pid < 0) {
        fail("clone3(CLONE_INTO_CGROUP|CLONE_PIDFD) failed; no fallback");
        close(gate[0]); close(gate[1]); close(groupfd); return BLOCKED;
    }
    if (pid == 0) {
        close(gate[0]);
        if (setsid() < 0) _exit(BLOCKED);
        char permit = 0;
        ssize_t count;
        do { count = read(gate[1], &permit, 1); } while (count < 0 && errno == EINTR);
        close(gate[1]);
        if (count != 1 || permit != 'G') _exit(BLOCKED);
        close(groupfd);
        /* Signals with handlers reset to default on successful execve. */
        execve(argv[4], argv + 4, environ);
        _exit(CHILD_EXEC_FAILURE);
    }
    close(gate[1]);
    int status = 0;
    if (stop_requested || !child_in_group(groupfd, pid) ||
        write_marker(argv[2], argv[1], pid) != 0 || stop_requested ||
        send(gate[0], "G", 1, MSG_NOSIGNAL) != 1) {
        fail("child membership/marker/launch gate not verified");
        close(gate[0]);
        (void)wait_bounded(pid, pidfd, &status);
        close(pidfd); close(groupfd);
        return BLOCKED;
    }
    close(gate[0]); close(groupfd);
    for (;;) {
        pid_t w = waitpid(pid, &status, 0);
        if (w == pid) break;
        if (w < 0 && errno == EINTR) {
            if (stop_requested) {
                if (wait_bounded(pid, pidfd, &status) != 0) {
                    fail("bounded abort could not reap owned child");
                }
                close(pidfd);
                return BLOCKED;
            }
            continue;
        }
        fail("waitpid owned child failed"); close(pidfd); return BLOCKED;
    }
    close(pidfd);
    if (stop_requested) return BLOCKED;
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return BLOCKED;
}
