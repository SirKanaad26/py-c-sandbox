// Minimal wrapper that doesn't depend on actual Snappy library
// This tests if the WASM build process works

#include <stddef.h>
#include <stdint.h>

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#define EXPORT EMSCRIPTEN_KEEPALIVE
#else
#define EXPORT
#endif

// Mock implementation for testing
EXPORT
size_t wasm_max_compressed_length(size_t source_length) {
    // Snappy's algorithm approximation: input + input/6 + 32
    return source_length + (source_length / 6) + 32;
}

EXPORT
int wasm_get_version(void) {
    return 1;
}

EXPORT
int wasm_test_function(int input) {
    return input * 2;
}
