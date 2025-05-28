#!/bin/bash
# Build WASM directly from Google's Snappy source code (actual source files)

set -e

echo "🔧 Building WASM from Real Snappy Source Files..."

# Create build directory
BUILD_DIR="snappy_direct_source"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download Snappy source if not already present
if [ ! -d "snappy" ]; then
    echo "📥 Downloading Google Snappy source code..."
    git clone https://github.com/google/snappy.git
    echo "✅ Downloaded Snappy repository"
fi

cd snappy

# Check if emscripten is available
if ! command -v emcc &> /dev/null; then
    echo "❌ Emscripten not found!"
    echo "Please install Emscripten SDK"
    exit 1
fi

echo "🔍 Configuring Snappy build..."
echo "📋 Repository info:"
echo "  Commit: $(git rev-parse --short HEAD)"
echo "  Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
echo "  Remote: $(git remote get-url origin)"
echo ""

# Check if we need to configure the build
if [ ! -f "snappy-stubs-public.h" ]; then
    echo "📦 Configuring Snappy with CMake..."
    
    # Create a build directory
    mkdir -p build_wasm
    cd build_wasm
    
    # Configure with emscripten
    emcmake cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DSNAPPY_BUILD_TESTS=OFF \
        -DSNAPPY_BUILD_BENCHMARKS=OFF
    
    # We don't need to build everything, just generate the config files
    echo "✅ Configuration complete"
    
    # Copy generated files back to source directory
    if [ -f "snappy-stubs-public.h" ]; then
        cp snappy-stubs-public.h ..
        echo "✅ Generated snappy-stubs-public.h"
    fi
    
    cd ..
else
    echo "✅ snappy-stubs-public.h already exists"
fi

# Verify required files exist
echo "🔍 Checking required files..."
REQUIRED_FILES=("snappy.cc" "snappy.h" "snappy-internal.h" "snappy-stubs-internal.h" "snappy-stubs-public.h")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
    fi
done
echo ""

# Create a minimal wrapper that exports just the function we need
cat > wasm_wrapper.cc << 'EOF'
// WASM wrapper for Google Snappy - uses actual source files
#include "snappy.h"

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

EXPORT
int GetVersion() {
    return 1;
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

echo "📋 Compiling these source files: $SNAPPY_SOURCES"
echo "📋 Plus wrapper: wasm_wrapper.cc"

# Compile with the actual Snappy source files
emcc $SNAPPY_SOURCES wasm_wrapper.cc \
     -I. \
     -s WASM=1 \
     -s STANDALONE_WASM=1 \
     -s EXPORTED_FUNCTIONS='["_MaxCompressedLength", "_GetVersion"]' \
     -s ALLOW_MEMORY_GROWTH=1 \
     -DHAVE_SYS_UIO_H=0 \
     -DHAVE_UNISTD_H=1 \
     -DSNAPPY_MAJOR=1 \
     -DSNAPPY_MINOR=1 \
     -DSNAPPY_PATCHLEVEL=9 \
     -O3 \
     --no-entry \
     -o snappy_direct.wasm

if [ -f "snappy_direct.wasm" ]; then
    FILE_SIZE=$(stat -f%z snappy_direct.wasm 2>/dev/null || stat -c%s snappy_direct.wasm 2>/dev/null || echo "unknown")
    echo "✅ WASM built from actual Snappy source files!"
    echo "📏 File size: $FILE_SIZE bytes"
    
    # Copy to parent directories for easy access
    cp snappy_direct.wasm ../..
    
    # Validate
    if command -v wasm-validate &> /dev/null; then
        if wasm-validate snappy_direct.wasm; then
            echo "✅ WASM validation passed!"
        fi
    fi
    
    echo "📋 Built from actual Google Snappy source files"
    echo "📋 Commit: $(git rev-parse HEAD)"
    
else
    echo "❌ Build failed!"
    echo "💡 Check the compilation output above for errors"
    exit 1
fi

cd ../..

echo ""
echo "🎉 Successfully built WASM from actual Snappy source files!"
echo "📦 Output: snappy_direct.wasm"
echo "🧬 This uses the unmodified Google Snappy source code"
echo "💡 Test with: python test_snappy_source.py"