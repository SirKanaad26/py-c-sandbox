#include <stdio.h>
#include <ctype.h>

void capitalize(char* str) {
    if (str == NULL) return;

    while (*str) {
        if (islower(*str)) {
            *str = toupper(*str);
        }
        str++;
    }
}
