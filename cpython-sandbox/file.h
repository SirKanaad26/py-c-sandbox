// simple_math.h
#ifndef SIMPLE_MATH_H
#define SIMPLE_MATH_H

#include <stdio.h>

// Function to calculate the square of a number
static inline int square(int num) {
    return num * num;
}

// Function to check if a number is even
static inline int is_even(int num) {
    return num % 2 == 0 ? 1 : 0;
}

// Print a demo message (helpful for testing WebAssembly output)
static inline void print_demo() {
    printf("Simple Math Library Loaded!\n");
    printf("Square of 5: %d\n", square(5));
    printf("Is 10 even? %s\n", is_even(10) ? "Yes" : "No");
}

#endif // SIMPLE_MATH_H