#ifndef COPY_ARRAY_TEST_H
#define COPY_ARRAY_TEST_H

void ensure_log_file();
void copy_array_overflow(int* dest, int* src, int len);
void copy_array_uaf(int* dest, int* src, int len);

#endif
