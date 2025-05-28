#include <stdio.h>
#include <ctype.h>
#include "capitalize.h"

void capitalize(char* str) {
    while (*str) {
        *str = toupper(*str);
        str++;
    }
}
