#include <stdio.h>

#include "__MOCK_LIB__.h"


int main(int argc, char **argv) {
    char const *res = __MOCK_LIB__();
    printf("__MOCK_NAME__:__MOCK_REV_NO__ %s\n", res);
    return 0;
}
