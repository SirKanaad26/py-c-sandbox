#!/bin/bash
# build_wasm.sh
# Script to build Snappy WebAssembly module

set -e  # Exit on any error

echo "🔧 Building Snappy WASM module..."

# Check if emcc is available
if ! command -v emcc &> /dev/null; then
    echo "❌ Error: Emscripten not found!"
    echo "Please install Emscripten first:"
    echo "  git clone https://github.com/emscripten-core/emsdk.git"
    echo "  cd emsdk"
    echo "  ./emsdk install latest"
    echo "  ./emsdk activate latest"
    echo "  source ./emsdk_env.sh"
    exit 1
fi

# Create build directory
mkdir -p wasm_build
cd wasm_build

echo "📁 Build directory: $(pwd)"

# Build Snappy for WASM first
if [ ! -f "libsnappy.a" ]; then
    echo "🏗️  Building Snappy for WebAssembly..."
    
    # Clone Snappy if not exists
    if [ ! -d "snappy-wasm" ]; then
        git clone https://github.com/google/snappy.git snappy-wasm
        cd snappy-wasm
        git submodule update --init  # Get test dependencies if needed
        cd ..
    fi
    
    cd snappy-wasm
    
    # Configure for WASM
    emcmake cmake . -DCMAKE_BUILD_TYPE=Release \
                    -DSNAPPY_BUILD_TESTS=OFF \
                    -DSNAPPY_BUILD_BENCHMARKS=OFF \
                    -DBUILD_SHARED_LIBS=OFF
    
    # Build
    emmake make -j$(nproc 2>/dev/null || echo 4)
    
    # Copy library and headers
    cp libsnappy.a ../
    cp snappy-c.h ../
    cp snappy.h ../
    cd ..
    
    echo "✅ Snappy built successfully!"
else
    echo "📚 Using existing Snappy library"
fi

# Build our WASM wrapper
echo "🔨 Building WASM wrapper..."

emcc ../wasm_wrapper.c \
     -L. -lsnappy \
     -I. \
     -s WASM=1 \
     -s EXPORTED_RUNTIME_METHODS='["cwrap", "ccall"]' \
     -s ALLOW_MEMORY_GROWTH=1 \
     -s MODULARIZE=1 \
     -s EXPORT_NAME='SnappyModule' \
     -O3 \
     -o snappy_wasm.js

echo "✅ WASM module built successfully!"
echo "📦 Files created:"
echo "   - snappy_wasm.js   (JavaScript loader)"
echo "   - snappy_wasm.wasm (WebAssembly binary)"

cd ..
echo "🎉 Build complete! Check the wasm_build/ directory."