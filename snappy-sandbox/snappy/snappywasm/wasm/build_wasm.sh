#!/bin/bash
# Build WASM directly from Google's Snappy source code (actual source files)
# Updated version with Uncompress, IsValidCompressedBuffer, and IsValidCompressed functions

set -e

echo "🔧 Building WASM from Real Snappy Source Files..."

# Create build directory
BUILD_DIR="snappy_source"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download Snappy source if not already present
if [ ! -d "snappy" ]; then
    echo "Downloading Google Snappy source code..."
    git clone https://github.com/google/snappy.git
    echo "Downloaded Snappy repository"
fi

cd snappy

# Check if emscripten is available
if ! command -v emcc &> /dev/null; then
    echo "Emscripten not found!"
    echo "Please install Emscripten SDK"
    exit 1
fi

echo "Configuring Snappy build..."
echo "Repository info:"
echo "  Commit: $(git rev-parse --short HEAD)"
echo "  Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
echo "  Remote: $(git remote get-url origin)"
echo ""

# Check if we need to configure the build
if [ ! -f "snappy-stubs-public.h" ]; then
    echo "Configuring Snappy with CMake..."
    
    # Create a build directory
    mkdir -p build_wasm
    cd build_wasm
    
    # Configure with emscripten
    emcmake cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DSNAPPY_BUILD_TESTS=OFF \
        -DSNAPPY_BUILD_BENCHMARKS=OFF
    
    # We don't need to build everything, just generate the config files
    echo "Configuration complete"
    
    # Copy generated files back to source directory
    if [ -f "snappy-stubs-public.h" ]; then
        cp snappy-stubs-public.h ..
        echo "Generated snappy-stubs-public.h"
    fi
    
    cd ..
else
    echo "snappy-stubs-public.h already exists"
fi

# Verify required files exist
echo "🔍 Checking required files..."
REQUIRED_FILES=("snappy.cc" "snappy.h" "snappy-internal.h" "snappy-stubs-internal.h" "snappy-stubs-public.h" "snappy-sinksource.h" "snappy-sinksource.cc")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  $file"
    else
        echo "  $file (missing)"
    fi
done
echo ""

# Create a minimal wrapper that exports the functions we need
cat > wasm_wrapper.cc << 'EOF'
// WASM wrapper for Google Snappy - uses actual source files
#include "snappy.h"
#include "snappy-sinksource.h"
#include <string>
#include <cstring>
#include <vector>
#include <sys/uio.h>

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#define EXPORT extern "C" EMSCRIPTEN_KEEPALIVE
#else
#define EXPORT extern "C" __attribute__((visibility("default")))
#endif

// Export the MaxCompressedLength function from the real Snappy library
EXPORT
size_t MaxCompressedLength(size_t source_length) {
    return snappy::MaxCompressedLength(source_length);
}

// Export the GetUncompressedLength function from the real Snappy library
EXPORT
bool GetUncompressedLength(const char* compressed, size_t compressed_length, size_t* result) {
    return snappy::GetUncompressedLength(compressed, compressed_length, result);
}

// Utility function to test GetUncompressedLength with a buffer allocated in WASM memory
EXPORT
int GetUncompressedLengthFromPtr(const char* compressed_ptr, size_t compressed_length, size_t* result_ptr) {
    bool success = snappy::GetUncompressedLength(compressed_ptr, compressed_length, result_ptr);
    return success ? 1 : 0; // Return 1 for success, 0 for failure
}

// Export the Compress function from the real Snappy library
EXPORT
size_t Compress(const char* input, size_t input_length, char* compressed_output, size_t max_compressed_length) {
    std::string compressed;
    size_t compressed_size = snappy::Compress(input, input_length, &compressed);
    
    // Check if output buffer is large enough
    if (compressed_size > max_compressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy compressed data to output buffer
    std::memcpy(compressed_output, compressed.data(), compressed_size);
    return compressed_size;
}

// Wrapper function that works with WASM memory pointers
EXPORT
size_t CompressFromPtr(const char* input_ptr, size_t input_length, char* output_ptr, size_t max_output_length) {
    return Compress(input_ptr, input_length, output_ptr, max_output_length);
}

// Export the IsValidCompressedBuffer function from the real Snappy library
EXPORT
bool IsValidCompressedBuffer(const char* compressed, size_t compressed_length) {
    return snappy::IsValidCompressedBuffer(compressed, compressed_length);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int IsValidCompressedBufferInt(const char* compressed_ptr, size_t compressed_length) {
    bool is_valid = snappy::IsValidCompressedBuffer(compressed_ptr, compressed_length);
    return is_valid ? 1 : 0; // Return 1 for valid, 0 for invalid
}

// NEW: Export the IsValidCompressed function that works with Source* parameter
// We create a C wrapper that takes raw buffer parameters and creates a ByteArraySource internally
EXPORT
bool IsValidCompressed(const char* compressed_data, size_t compressed_length) {
    // Create a ByteArraySource from the raw buffer data
    snappy::ByteArraySource source(compressed_data, compressed_length);
    // Call the real Snappy IsValidCompressed function
    return snappy::IsValidCompressed(&source);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int IsValidCompressedInt(const char* compressed_ptr, size_t compressed_length) {
    bool is_valid = IsValidCompressed(compressed_ptr, compressed_length);
    return is_valid ? 1 : 0; // Return 1 for valid, 0 for invalid
}

// Export the RawUncompress function from the real Snappy library (char* buffer version)
EXPORT
bool RawUncompress(const char* compressed, size_t compressed_length, char* uncompressed) {
    return snappy::RawUncompress(compressed, compressed_length, uncompressed);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int RawUncompressInt(const char* compressed_ptr, size_t compressed_length, char* uncompressed_ptr) {
    bool success = snappy::RawUncompress(compressed_ptr, compressed_length, uncompressed_ptr);
    return success ? 1 : 0; // Return 1 for success, 0 for failure
}

// Export the RawUncompress function that works with Source* parameter (similar to IsValidCompressed)
// We create a C wrapper that takes raw buffer parameters and creates a ByteArraySource internally
EXPORT
bool RawUncompressFromSource(const char* compressed_data, size_t compressed_length, char* uncompressed) {
    // Create a ByteArraySource from the raw buffer data
    snappy::ByteArraySource source(compressed_data, compressed_length);
    // Call the real Snappy RawUncompress function with Source*
    return snappy::RawUncompress(&source, uncompressed);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int RawUncompressFromSourceInt(const char* compressed_ptr, size_t compressed_length, char* uncompressed_ptr) {
    bool success = RawUncompressFromSource(compressed_ptr, compressed_length, uncompressed_ptr);
    return success ? 1 : 0; // Return 1 for success, 0 for failure
}

// Export the RawUncompressToIOVec function from the real Snappy library (char* buffer version)
EXPORT
bool RawUncompressToIOVec(const char* compressed, size_t compressed_length, const void* iov_ptr, size_t iov_cnt) {
    // Convert the WASM memory pointer to iovec structures
    // Each iovec structure contains: void* iov_base, size_t iov_len
    // In WASM (32-bit), each iovec is 8 bytes: 4 bytes ptr + 4 bytes len
    
    const uint32_t* iov_data = static_cast<const uint32_t*>(iov_ptr);
    std::vector<struct iovec> iovecs(iov_cnt);
    
    // Convert WASM iovec format to native iovec format
    for (size_t i = 0; i < iov_cnt; i++) {
        uint32_t base_offset = iov_data[i * 2];     // iov_base as offset
        uint32_t length = iov_data[i * 2 + 1];     // iov_len
        
        // Convert offset to actual pointer (assuming base of WASM memory)
        iovecs[i].iov_base = reinterpret_cast<void*>(base_offset);
        iovecs[i].iov_len = length;
    }
    
    // Call the real Snappy RawUncompressToIOVec function
    return snappy::RawUncompressToIOVec(compressed, compressed_length, iovecs.data(), iov_cnt);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int RawUncompressToIOVecInt(const char* compressed_ptr, size_t compressed_length, const void* iov_ptr, size_t iov_cnt) {
    bool success = RawUncompressToIOVec(compressed_ptr, compressed_length, iov_ptr, iov_cnt);
    return success ? 1 : 0; // Return 1 for success, 0 for failure
}

// Export the RawUncompressToIOVec function that works with Source* parameter
// We create a C wrapper that takes raw buffer parameters and creates a ByteArraySource internally
EXPORT
bool RawUncompressToIOVecFromSource(const char* compressed_data, size_t compressed_length, const void* iov_ptr, size_t iov_cnt) {
    // Convert the WASM memory pointer to iovec structures
    const uint32_t* iov_data = static_cast<const uint32_t*>(iov_ptr);
    std::vector<struct iovec> iovecs(iov_cnt);
    
    // Convert WASM iovec format to native iovec format
    for (size_t i = 0; i < iov_cnt; i++) {
        uint32_t base_offset = iov_data[i * 2];     // iov_base as offset
        uint32_t length = iov_data[i * 2 + 1];     // iov_len
        
        // Convert offset to actual pointer
        iovecs[i].iov_base = reinterpret_cast<void*>(base_offset);
        iovecs[i].iov_len = length;
    }
    
    // Create a ByteArraySource from the raw buffer data
    snappy::ByteArraySource source(compressed_data, compressed_length);
    // Call the real Snappy RawUncompressToIOVec function with Source*
    return snappy::RawUncompressToIOVec(&source, iovecs.data(), iov_cnt);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int RawUncompressToIOVecFromSourceInt(const char* compressed_ptr, size_t compressed_length, const void* iov_ptr, size_t iov_cnt) {
    bool success = RawUncompressToIOVecFromSource(compressed_ptr, compressed_length, iov_ptr, iov_cnt);
    return success ? 1 : 0; // Return 1 for success, 0 for failure
}

// Simplified RawUncompressToIOVec that takes flattened buffer pointers and lengths
// This is easier to use from WASM since it doesn't require complex iovec handling
EXPORT
bool RawUncompressToBuffers(const char* compressed, size_t compressed_length, char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count) {
    // Create iovec structures from the flattened output buffers
    std::vector<struct iovec> iovecs(buffer_count);
    size_t current_offset = 0;
    
    for (size_t i = 0; i < buffer_count; i++) {
        iovecs[i].iov_base = buffer_ptr + current_offset;
        iovecs[i].iov_len = lengths_ptr[i];
        current_offset += lengths_ptr[i];
    }
    
    // Call the real Snappy RawUncompressToIOVec function
    return snappy::RawUncompressToIOVec(compressed, compressed_length, iovecs.data(), buffer_count);
}

// Alternative wrapper that explicitly returns int for clarity
EXPORT
int RawUncompressToBuffersInt(const char* compressed_ptr, size_t compressed_length, char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count) {
    bool success = RawUncompressToBuffers(compressed_ptr, compressed_length, buffer_ptr, lengths_ptr, buffer_count);
    return success ? 1 : 0; // Return 1 for success, 0 for failure
}

// Export the Uncompress function from the real Snappy library
EXPORT
size_t Uncompress(const char* compressed, size_t compressed_length, char* uncompressed_output, size_t max_uncompressed_length) {
    std::string uncompressed;
    
    // Call the real Snappy Uncompress function
    bool success = snappy::Uncompress(compressed, compressed_length, &uncompressed);
    
    if (!success) {
        return 0; // Error: decompression failed
    }
    
    // Check if output buffer is large enough
    if (uncompressed.size() > max_uncompressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy uncompressed data to output buffer
    std::memcpy(uncompressed_output, uncompressed.data(), uncompressed.size());
    return uncompressed.size();
}

// Wrapper function for Uncompress that works with WASM memory pointers
EXPORT
size_t UncompressFromPtr(const char* compressed_ptr, size_t compressed_length, char* output_ptr, size_t max_output_length) {
    return Uncompress(compressed_ptr, compressed_length, output_ptr, max_output_length);
}

// Export the Compress function with CompressionOptions from the real Snappy library
EXPORT
size_t CompressWithOptions(const char* input, size_t input_length, char* compressed_output, size_t max_compressed_length, int compression_level) {
    // Create CompressionOptions with the specified level
    snappy::CompressionOptions options;
    options.level = compression_level;
    
    std::string compressed;
    size_t compressed_size = snappy::Compress(input, input_length, &compressed, options);
    
    // Check if output buffer is large enough
    if (compressed_size > max_compressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy compressed data to output buffer
    std::memcpy(compressed_output, compressed.data(), compressed_size);
    return compressed_size;
}

// Wrapper function for CompressWithOptions that works with WASM memory pointers
EXPORT
size_t CompressWithOptionsFromPtr(const char* input_ptr, size_t input_length, char* output_ptr, size_t max_output_length, int compression_level) {
    return CompressWithOptions(input_ptr, input_length, output_ptr, max_output_length, compression_level);
}

// Utility functions for CompressionOptions
EXPORT
int GetMinCompressionLevel() {
    return snappy::CompressionOptions::MinCompressionLevel();
}

EXPORT
int GetMaxCompressionLevel() {
    return snappy::CompressionOptions::MaxCompressionLevel();
}

EXPORT
int GetDefaultCompressionLevel() {
    return snappy::CompressionOptions::DefaultCompressionLevel();
}

// Export CompressFromIOVec function from the real Snappy library
// Note: This function takes multiple input buffers and compresses them as one stream
EXPORT
size_t CompressFromIOVec(const void* iov_ptr, size_t iov_cnt, char* compressed_output, size_t max_compressed_length) {
    // Convert the WASM memory pointer to iovec structures
    // Each iovec structure contains: void* iov_base, size_t iov_len
    // In WASM (32-bit), each iovec is 8 bytes: 4 bytes ptr + 4 bytes len
    
    const uint32_t* iov_data = static_cast<const uint32_t*>(iov_ptr);
    std::vector<struct iovec> iovecs(iov_cnt);
    
    // Convert WASM iovec format to native iovec format
    for (size_t i = 0; i < iov_cnt; i++) {
        uint32_t base_offset = iov_data[i * 2];     // iov_base as offset
        uint32_t length = iov_data[i * 2 + 1];     // iov_len
        
        // Convert offset to actual pointer (assuming base of WASM memory)
        iovecs[i].iov_base = reinterpret_cast<void*>(base_offset);
        iovecs[i].iov_len = length;
    }
    
    std::string compressed;
    size_t compressed_size = snappy::CompressFromIOVec(iovecs.data(), iov_cnt, &compressed);
    
    // Check if output buffer is large enough
    if (compressed_size > max_compressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy compressed data to output buffer
    std::memcpy(compressed_output, compressed.data(), compressed_size);
    return compressed_size;
}

// Simplified CompressFromIOVec that takes flattened buffer pointers and lengths
// This is easier to use from WASM since it doesn't require complex iovec handling
EXPORT
size_t CompressFromBuffers(const char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count, 
                          char* compressed_output, size_t max_compressed_length) {
    // Create iovec structures from the flattened input
    std::vector<struct iovec> iovecs(buffer_count);
    size_t current_offset = 0;
    
    for (size_t i = 0; i < buffer_count; i++) {
        iovecs[i].iov_base = const_cast<char*>(buffer_ptr + current_offset);
        iovecs[i].iov_len = lengths_ptr[i];
        current_offset += lengths_ptr[i];
    }
    
    std::string compressed;
    size_t compressed_size = snappy::CompressFromIOVec(iovecs.data(), buffer_count, &compressed);
    
    // Check if output buffer is large enough
    if (compressed_size > max_compressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy compressed data to output buffer
    std::memcpy(compressed_output, compressed.data(), compressed_size);
    return compressed_size;
}

// CompressFromIOVec with CompressionOptions
EXPORT
size_t CompressFromIOVecWithOptions(const void* iov_ptr, size_t iov_cnt, char* compressed_output, 
                                   size_t max_compressed_length, int compression_level) {
    // Convert the WASM memory pointer to iovec structures
    const uint32_t* iov_data = static_cast<const uint32_t*>(iov_ptr);
    std::vector<struct iovec> iovecs(iov_cnt);
    
    // Convert WASM iovec format to native iovec format
    for (size_t i = 0; i < iov_cnt; i++) {
        uint32_t base_offset = iov_data[i * 2];     // iov_base as offset
        uint32_t length = iov_data[i * 2 + 1];     // iov_len
        
        // Convert offset to actual pointer
        iovecs[i].iov_base = reinterpret_cast<void*>(base_offset);
        iovecs[i].iov_len = length;
    }
    
    // Create CompressionOptions with the specified level
    snappy::CompressionOptions options;
    options.level = compression_level;
    
    std::string compressed;
    size_t compressed_size = snappy::CompressFromIOVec(iovecs.data(), iov_cnt, &compressed, options);
    
    // Check if output buffer is large enough
    if (compressed_size > max_compressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy compressed data to output buffer
    std::memcpy(compressed_output, compressed.data(), compressed_size);
    return compressed_size;
}

// Simplified version with CompressionOptions
EXPORT
size_t CompressFromBuffersWithOptions(const char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count,
                                     char* compressed_output, size_t max_compressed_length, int compression_level) {
    // Create iovec structures from the flattened input
    std::vector<struct iovec> iovecs(buffer_count);
    size_t current_offset = 0;
    
    for (size_t i = 0; i < buffer_count; i++) {
        iovecs[i].iov_base = const_cast<char*>(buffer_ptr + current_offset);
        iovecs[i].iov_len = lengths_ptr[i];
        current_offset += lengths_ptr[i];
    }
    
    // Create CompressionOptions with the specified level
    snappy::CompressionOptions options;
    options.level = compression_level;
    
    std::string compressed;
    size_t compressed_size = snappy::CompressFromIOVec(iovecs.data(), buffer_count, &compressed, options);
    
    // Check if output buffer is large enough
    if (compressed_size > max_compressed_length) {
        return 0; // Error: output buffer too small
    }
    
    // Copy compressed data to output buffer
    std::memcpy(compressed_output, compressed.data(), compressed_size);
    return compressed_size;
}

// ========================================
// ADD THESE FUNCTIONS TO YOUR wasm_wrapper.cc 
// (Insert after the existing functions, before the GetVersion() function)
// ========================================

// NEW: Export the RawCompress function from the real Snappy library
// void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length);
EXPORT
void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length) {
    snappy::RawCompress(input, input_length, compressed, compressed_length);
}

// NEW: Export the RawCompress function with CompressionOptions from the real Snappy library
// void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length, CompressionOptions options);
EXPORT
void RawCompressWithOptions(const char* input, size_t input_length, char* compressed, size_t* compressed_length, int compression_level) {
    snappy::CompressionOptions options;
    options.level = compression_level;
    snappy::RawCompress(input, input_length, compressed, compressed_length, options);
}

// NEW: Export the RawCompressFromIOVec function from the real Snappy library
// void RawCompressFromIOVec(const struct iovec* iov, size_t uncompressed_length, char* compressed, size_t* compressed_length);
EXPORT
void RawCompressFromIOVec(const void* iov_ptr, size_t iov_cnt, size_t uncompressed_length, char* compressed, size_t* compressed_length) {
    const uint32_t* iov_data = static_cast<const uint32_t*>(iov_ptr);
    std::vector<struct iovec> iovecs(iov_cnt);
    
    // Convert WASM iovec format to native iovec format
    for (size_t i = 0; i < iov_cnt; i++) {
        uint32_t base_offset = iov_data[i * 2];     // iov_base as offset
        uint32_t length = iov_data[i * 2 + 1];     // iov_len
        
        // Convert offset to actual pointer
        iovecs[i].iov_base = reinterpret_cast<void*>(base_offset);
        iovecs[i].iov_len = length;
    }
    
    // Call the real Snappy RawCompressFromIOVec function
    snappy::RawCompressFromIOVec(iovecs.data(), uncompressed_length, compressed, compressed_length);
}

// NEW: Export the RawCompressFromIOVec function with CompressionOptions from the real Snappy library
// void RawCompressFromIOVec(const struct iovec* iov, size_t uncompressed_length, char* compressed, size_t* compressed_length, CompressionOptions options);
EXPORT
void RawCompressFromIOVecWithOptions(const void* iov_ptr, size_t iov_cnt, size_t uncompressed_length, char* compressed, size_t* compressed_length, int compression_level) {
    const uint32_t* iov_data = static_cast<const uint32_t*>(iov_ptr);
    std::vector<struct iovec> iovecs(iov_cnt);
    
    // Convert WASM iovec format to native iovec format
    for (size_t i = 0; i < iov_cnt; i++) {
        uint32_t base_offset = iov_data[i * 2];     // iov_base as offset
        uint32_t length = iov_data[i * 2 + 1];     // iov_len
        
        // Convert offset to actual pointer
        iovecs[i].iov_base = reinterpret_cast<void*>(base_offset);
        iovecs[i].iov_len = length;
    }
    
    // Create CompressionOptions with the specified level
    snappy::CompressionOptions options;
    options.level = compression_level;
    
    // Call the real Snappy RawCompressFromIOVec function with options
    snappy::RawCompressFromIOVec(iovecs.data(), uncompressed_length, compressed, compressed_length, options);
}

// Simplified RawCompressFromIOVec that takes flattened buffer pointers and lengths
// This is easier to use from WASM since it doesn't require complex iovec handling
EXPORT
void RawCompressFromBuffers(const char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count, 
                           size_t uncompressed_length, char* compressed, size_t* compressed_length) {
    // Create iovec structures from the flattened input buffers
    std::vector<struct iovec> iovecs(buffer_count);
    size_t current_offset = 0;
    
    for (size_t i = 0; i < buffer_count; i++) {
        iovecs[i].iov_base = const_cast<char*>(buffer_ptr + current_offset);
        iovecs[i].iov_len = lengths_ptr[i];
        current_offset += lengths_ptr[i];
    }
    
    // Call the real Snappy RawCompressFromIOVec function
    snappy::RawCompressFromIOVec(iovecs.data(), uncompressed_length, compressed, compressed_length);
}

// RawCompressFromBuffers with CompressionOptions
EXPORT
void RawCompressFromBuffersWithOptions(const char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count,
                                      size_t uncompressed_length, char* compressed, size_t* compressed_length, int compression_level) {
    // Create iovec structures from the flattened input buffers
    std::vector<struct iovec> iovecs(buffer_count);
    size_t current_offset = 0;
    
    for (size_t i = 0; i < buffer_count; i++) {
        iovecs[i].iov_base = const_cast<char*>(buffer_ptr + current_offset);
        iovecs[i].iov_len = lengths_ptr[i];
        current_offset += lengths_ptr[i];
    }
    
    // Create CompressionOptions with the specified level
    snappy::CompressionOptions options;
    options.level = compression_level;
    
    // Call the real Snappy RawCompressFromIOVec function with options
    snappy::RawCompressFromIOVec(iovecs.data(), uncompressed_length, compressed, compressed_length, options);
}

// Custom Sink implementation for WASM that writes to a pre-allocated buffer
class WASMSink : public snappy::Sink {
public:
    WASMSink(char* buffer, size_t max_size) : buffer_(buffer), max_size_(max_size), written_(0) {}
    
    virtual void Append(const char* bytes, size_t n) override {
        if (written_ + n <= max_size_) {
            std::memcpy(buffer_ + written_, bytes, n);
            written_ += n;
        } else {
            // Buffer overflow - you might want to handle this differently
            overflow_ = true;
        }
    }
    
    virtual char* GetAppendBuffer(size_t length, char* scratch) override {
        if (written_ + length <= max_size_) {
            return buffer_ + written_;
        }
        return scratch; // Fallback to scratch buffer
    }
    
    size_t bytes_written() const { return written_; }
    bool overflow() const { return overflow_; }
    
private:
    char* buffer_;
    size_t max_size_;
    size_t written_;
    bool overflow_ = false;
};

// Custom Source implementation for WASM that reads from a buffer
class WASMSource : public snappy::Source {
public:
    WASMSource(const char* buffer, size_t size) : buffer_(buffer), size_(size), pos_(0) {}
    
    virtual size_t Available() const override {
        return size_ - pos_;
    }
    
    virtual const char* Peek(size_t* len) override {
        *len = size_ - pos_;
        return buffer_ + pos_;
    }
    
    virtual void Skip(size_t n) override {
        pos_ = std::min(pos_ + n, size_);
    }
    
private:
    const char* buffer_;
    size_t size_;
    size_t pos_;
};

// NEW: Export the Compress function with Source/Sink from the real Snappy library
// size_t Compress(Source* reader, Sink* writer);
EXPORT
size_t CompressFromSourceToSink(const char* input_buffer, size_t input_length, char* output_buffer, size_t max_output_length) {
    WASMSource source(input_buffer, input_length);
    WASMSink sink(output_buffer, max_output_length);
    
    size_t compressed_size = snappy::Compress(&source, &sink);
    
    if (sink.overflow()) {
        return 0; // Error: output buffer too small
    }
    
    return compressed_size;
}

// NEW: Export the Compress function with Source/Sink and CompressionOptions from the real Snappy library
// size_t Compress(Source* reader, Sink* writer, CompressionOptions options);
EXPORT
size_t CompressFromSourceToSinkWithOptions(const char* input_buffer, size_t input_length, char* output_buffer, size_t max_output_length, int compression_level) {
    WASMSource source(input_buffer, input_length);
    WASMSink sink(output_buffer, max_output_length);
    
    snappy::CompressionOptions options;
    options.level = compression_level;
    
    size_t compressed_size = snappy::Compress(&source, &sink, options);
    
    if (sink.overflow()) {
        return 0; // Error: output buffer too small
    }
    
    return compressed_size;
}

// Export memory allocation functions for managing WASM memory from Python
EXPORT
void* AllocateMemory(size_t size) {
    return malloc(size);
}

EXPORT
void FreeMemory(void* ptr) {
    free(ptr);
}

// Utility function to copy data into WASM memory (for testing)
EXPORT
void WriteToMemory(void* dest, const char* src, size_t size) {
    std::memcpy(dest, src, size);
}

// Utility function to read data from WASM memory (for testing)
EXPORT
void ReadFromMemory(const void* src, char* dest, size_t size) {
    std::memcpy(dest, src, size);
}

EXPORT
int GetVersion() {
    return 11; // Version 11 - now includes RawCompress, RawCompressFromIOVec, and Source/Sink Compress functions
}
EOF

echo "🔨 Compiling actual Snappy source files to WASM..."

# Find all the necessary source files
SNAPPY_SOURCES=""
if [ -f "snappy.cc" ]; then
    SNAPPY_SOURCES="$SNAPPY_SOURCES snappy.cc"
fi
if [ -f "snappy-sinksource.cc" ]; then
    SNAPPY_SOURCES="$SNAPPY_SOURCES snappy-sinksource.cc"
fi
if [ -f "snappy-stubs-internal.cc" ]; then
    SNAPPY_SOURCES="$SNAPPY_SOURCES snappy-stubs-internal.cc"
fi

echo "Compiling these source files: $SNAPPY_SOURCES"
echo "Plus wrapper: wasm_wrapper.cc"

# Compile with the actual Snappy source files
emcc $SNAPPY_SOURCES wasm_wrapper.cc \
     -I. \
     -s WASM=1 \
     -s STANDALONE_WASM=1 \
     -s EXPORTED_FUNCTIONS='["_MaxCompressedLength", "_GetUncompressedLength", "_GetUncompressedLengthFromPtr", "_Compress", "_CompressFromPtr", "_CompressWithOptions", "_CompressWithOptionsFromPtr", "_CompressFromIOVec", "_CompressFromBuffers", "_CompressFromIOVecWithOptions", "_CompressFromBuffersWithOptions", "_RawCompress", "_RawCompressWithOptions", "_RawCompressFromIOVec", "_RawCompressFromIOVecWithOptions", "_RawCompressFromBuffers", "_RawCompressFromBuffersWithOptions", "_CompressFromSourceToSink", "_CompressFromSourceToSinkWithOptions", "_IsValidCompressedBuffer", "_IsValidCompressedBufferInt", "_IsValidCompressed", "_IsValidCompressedInt", "_RawUncompress", "_RawUncompressInt", "_RawUncompressFromSource", "_RawUncompressFromSourceInt", "_RawUncompressToIOVec", "_RawUncompressToIOVecInt", "_RawUncompressToIOVecFromSource", "_RawUncompressToIOVecFromSourceInt", "_RawUncompressToBuffers", "_RawUncompressToBuffersInt", "_Uncompress", "_UncompressFromPtr", "_GetMinCompressionLevel", "_GetMaxCompressionLevel", "_GetDefaultCompressionLevel", "_AllocateMemory", "_FreeMemory", "_WriteToMemory", "_ReadFromMemory", "_GetVersion"]' \
     -s ALLOW_MEMORY_GROWTH=1 \
     -DHAVE_SYS_UIO_H=1 \
     -DHAVE_UNISTD_H=1 \
     -O3 \
     --no-entry \
     -o snappy.wasm

if [ -f "snappy.wasm" ]; then
    FILE_SIZE=$(stat -f%z snappy.wasm 2>/dev/null || stat -c%s snappy.wasm 2>/dev/null || echo "unknown")
    echo "WASM built from actual Snappy source files!"
    echo "File size: $FILE_SIZE bytes"
    
    # Copy to parent directories for easy access
    cp snappy.wasm ../..
    
    # Validate
    if command -v wasm-validate &> /dev/null; then
        if wasm-validate snappy.wasm; then
            echo "WASM validation passed!"
        fi
    fi
    
    echo "Built from actual Google Snappy source files"
    echo "Commit: $(git rev-parse HEAD)"
    
else
    echo "Build failed!"
    echo "Check the compilation output above for errors"
    exit 1
fi

cd ../..

echo ""
echo "Successfully built WASM from actual Snappy source files!"
echo "Output: snappy.wasm"
echo "This uses the unmodified Google Snappy source code"
echo "Available functions:"
echo "  • MaxCompressedLength - Calculate max size needed for compression"
echo "  • GetUncompressedLength / GetUncompressedLengthFromPtr - Get original size from compressed data"
echo "  • Compress / CompressFromPtr - Compress data (default compression level)"
echo "  • CompressWithOptions / CompressWithOptionsFromPtr - Compress data with specific compression level"
echo "  • CompressFromIOVec / CompressFromBuffers - Compress from multiple input buffers"
echo "  • CompressFromIOVecWithOptions / CompressFromBuffersWithOptions - Compress from multiple buffers with compression level"
echo "  • Uncompress / UncompressFromPtr - Decompress data"
echo "  • RawUncompress / RawUncompressInt - Raw decompression (char* buffer version)"
echo "  • RawUncompressFromSource / RawUncompressFromSourceInt - Raw decompression (using Source* internally)"
echo "  • RawUncompressToIOVec / RawUncompressToIOVecInt - Raw decompression to multiple buffers (char* version)"
echo "  • RawUncompressToIOVecFromSource / RawUncompressToIOVecFromSourceInt - Raw decompression to multiple buffers (using Source* internally)"
echo "  • RawUncompressToBuffers / RawUncompressToBuffersInt - Simplified raw decompression to multiple buffers"
echo "  • IsValidCompressedBuffer / IsValidCompressedBufferInt - Validate compressed data (char* buffer)"
echo "  • IsValidCompressed / IsValidCompressedInt - Validate compressed data (using Source* internally)"
echo "  • GetMinCompressionLevel / GetMaxCompressionLevel / GetDefaultCompressionLevel - Compression level utilities"
echo "  • Memory management utilities"
echo "Test with: python test_snappy_source.py"