#define _GNU_SOURCE
#include <errno.h>
#include <linux/sched.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void) {
#ifdef SYS_clone3
    struct clone_args args = {0};
    args.exit_signal = SIGCHLD;
    long pid = syscall(SYS_clone3, &args, sizeof(args));
    if (pid < 0) {
        printf("clone3_basic=BLOCKED errno=%d reason=%s\n", errno, strerror(errno));
        return 2;
    }
    if (pid == 0) _exit(0);
    int status = 0;
    if (waitpid((pid_t)pid, &status, 0) != pid) {
        puts("clone3_basic=ERROR waitpid");
        return 3;
    }
    printf("clone3_basic=AVAILABLE child_exit=%d\n", WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    return 0;
#else
    puts("clone3_basic=UNAVAILABLE SYS_clone3 not defined by headers");
    return 2;
#endif
}
