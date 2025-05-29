#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static FILE* log_file = NULL;

void ensure_log_file() {
    if (!log_file) {
        log_file = fopen("../logs.log", "a");
        if (!log_file) {
            fprintf(stderr, "Could not open log file for writing\n");
        }
    }
}

void copy_array_overflow(int* dest, int* src, int len) {
    ensure_log_file();
    fprintf(log_file, "[C: overflow] Executing buffer overflow logic\n");
    fflush(log_file);

    printf("[C: overflow] Simulating buffer overflow\n");
    // memcpy(dest, src, (len + 5) * sizeof(int));
}

void copy_array_uaf(int* dest, int* src, int len) {
    ensure_log_file();
    fprintf(log_file, "[C: uaf] Executing use-after-free logic\n");
    fflush(log_file);

    printf("[C: uaf] Simulating use-after-free\n");
    // int* tmp = malloc(len * sizeof(int));
    // free(tmp);
    // memcpy(dest, tmp, len * sizeof(int));
}
