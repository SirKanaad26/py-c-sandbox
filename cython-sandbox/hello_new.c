#include <stdio.h>
#include "hello.h"

// Add these export attributes
__attribute__((export_name("hello_world")))
void hello_world(void) {
    printf("Hello, World from WebAssembly!\n");
}

__attribute__((export_name("calculate")))
int calculate(int a, int b) {
    return a * b + a;
}

// Main function
int main() {
    hello_world();
    int result = calculate(5, 3);
    printf("Result: %d\n", result);
    return 0;
}