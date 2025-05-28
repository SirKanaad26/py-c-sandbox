// crash.c
#include <string.h>
#include <stdio.h>

char* invalid_ptr = NULL;
char source[20] = "ExploitTest";

// int main() {
//     return 0;
// }

void unsafe_memcpy() {
    printf("[*] Triggering unsafe memcpy...\n");
    memcpy(invalid_ptr, source, strlen(source));
    printf("[*] Finished unsafe memcpy.\n");
}