extern "C" {
    #include <stddef.h>  // for size_t
}

// Include snappy *after* extern "C" to avoid mangling your wrapper
#include "snappy.h"
#include "snappy.cc"  // If needed; or link during build

// C-style wrapper for Cython
extern "C" size_t cython_MaxCompressedLength(size_t source_bytes) {
    return snappy::MaxCompressedLength(source_bytes);  // snappy:: namespace if needed
}
