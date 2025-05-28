// wasm_wrapper.c
// C wrapper for Snappy functions to be compiled to WebAssembly

#include <stddef.h>
#include <stdint.h>
#include "snappy-c.h"

// Export functions to JavaScript
// The EMSCRIPTEN_KEEPALIVE macro ensures these functions are exported

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#define EXPORT EMSCRIPTEN_KEEPALIVE
#else
#define EXPORT
#endif

/**
 * Simple wrapper for snappy_max_compressed_length
 * Returns the maximum possible size of compressed data
 */
EXPORT
size_t wasm_max_compressed_length(size_t source_length) {
    return snappy_max_compressed_length(source_length);
}

/**
 * Get version info (useful for testing)
 * Returns a simple version number
 */
EXPORT
int wasm_get_version(void) {
    return 1; // Simple version identifier
}

/**
 * Test function to verify WASM is working
 * Returns the input value doubled
 */
EXPORT
int wasm_test_function(int input) {
    return input * 2;
}