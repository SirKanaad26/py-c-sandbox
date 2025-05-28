#include <stdio.h>
#include <string.h>

int evil_overflow(int* src, int len) {
    volatile int buffer[3];
    volatile int buffer2[3];

    buffer2[0] = 100;

    printf("Address of buffer2: %p\n", (void*)&buffer2);
    printf("Address of buffer: %p\n", (void*)buffer);
    printf("BEFORE overflow: buffer2 = %d\n", buffer2[0]);

    memcpy(buffer, src, len * sizeof(int));  // Vulnerability
    printf("after copying into buffer, but BEFORE overflow: buffer = %d\n", buffer[0]);

    memcpy(buffer2, src, len * sizeof(int));  // Vulnerability

    printf("AFTER overflow: buffer2 = %d\n", buffer2[0]);
    printf("after copying buffer 2 (which overflows to change buffer 1) buffer = %d\n", buffer[0]);
    return buffer[0];
}
