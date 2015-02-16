#include <stdio.h>

#include "foo.h"


int main(int argc, char **argv) {
    char const *foores = foo();
    printf("%sbar\n", foores);
    return 0;
}
