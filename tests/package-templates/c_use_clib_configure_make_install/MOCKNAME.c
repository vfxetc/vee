#include <stdio.h>

#include "MOCKLIB.h"


int main(int argc, char **argv) {
    char const *res = MOCKLIB();
    printf("MOCKNAME:MOCKREVNO %s\n", res);
    return 0;
}
