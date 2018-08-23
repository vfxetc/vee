#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>


// The mechanics of string expansion are odd.
#define _STR_EXPAND(tok) #tok
#define STR(tok) _STR_EXPAND(tok)


// This is a way to easily define more binaries that are subcommands of `vee`,
// e.g. `dev`.
#ifndef VEE_PREPEND_ARGS
    #define VEE_PREPEND_ARGS
#endif


char ** copy_array(char **dst, char **src, unsigned int n) {
    while (n--) {
        *(dst++) = *(src++);
    }
    return dst;
}

int main(int argc, char **argv) {

    int i;

    char *python = getenv("VEE_PYTHON");
    if (!python) {
        python = "python";
    }

    // We build in the path to the bootstrap, as we don't have a good method
    // of figuring out our own abspath.
    char *bootstrap = STR(VEE_SRC_BIN) "/_vee_bootstrap.py";

    char *extra_argv[] = { VEE_PREPEND_ARGS };
    int extra_argc = sizeof(extra_argv) / sizeof(char*);

    int new_argc = 1 + extra_argc + argc; // 1 here is for bootstrap.
    char **new_argv = malloc((new_argc + 1) * sizeof(char*)); // 1 here is for NULL.

    char **new_arg = new_argv;

    *(new_arg++) = python;
    *(new_arg++) = bootstrap;

    new_arg = copy_array(new_arg, extra_argv, extra_argc);
    new_arg = copy_array(new_arg, argv + 1  , argc - 1);

    *(new_arg++) = 0;

    if (!getenv("VEE_BOOTSTRAP_NOEXEC")) {
        execvp(new_argv[0], new_argv);
        fprintf(stderr, "ERROR during VEE bootstrap: ");
    }

    for (i = 0; i < new_argc + 1; i++) {
        fprintf(stderr, "%s ", new_argv[i]);
    }
    fprintf(stderr, "\n");

    return -1;

}
