// hello.h

#ifndef HELLO_H
#define HELLO_H

#include <stdio.h>
#include <string.h>  // for memcpy

void copy_array(int* dest, int* src, int len) {
    printf("main");
    memcpy(dest, src, len * sizeof(int));
}

#endif // HELLO_H
