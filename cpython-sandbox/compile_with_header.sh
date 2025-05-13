#!/bin/bash

# First, we need to install wasi-sdk which provides the correct standard libraries for WebAssembly
if [ ! -d "wasi-sdk" ]; then
    echo "Downloading WASI SDK (provides standard library for WebAssembly)..."
    
    # Determine OS and architecture
    if [[ "$(uname)" == "Darwin" ]]; then
        if [[ "$(uname -m)" == "arm64" ]]; then
            # M1/M2 Mac
            WASI_SDK_URL="https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-macos-arm64.tar.gz"
        else
            # Intel Mac
            WASI_SDK_URL="https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-macos.tar.gz"
        fi
    else
        # Linux
        WASI_SDK_URL="https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-linux.tar.gz"
    fi
    
    curl -L $WASI_SDK_URL -o wasi-sdk.tar.gz
    mkdir -p wasi-sdk
    tar xf wasi-sdk.tar.gz -C wasi-sdk --strip-components=1
    rm wasi-sdk.tar.gz
    
    echo "WASI SDK installed!"
fi

# Set up paths
WASI_SDK_PATH="$(pwd)/wasi-sdk"
SYSROOT="$WASI_SDK_PATH/share/wasi-sysroot"

# Make sure the source files exist
if [ ! -f "hello.h" ] || [ ! -f "hello_new.c" ]; then
    echo "Error: Required files hello.h and hello_new.c not found!"
    exit 1
fi

# Display versions
echo "Using clang: $(clang --version | head -n 1)"
echo "Using WASI SDK from: $WASI_SDK_PATH"

# Compilation flags
CFLAGS="-O0 -g3 -fno-inline -fno-optimize-sibling-calls"

# Add WASI sysroot to include paths
CFLAGS="$CFLAGS --sysroot=$SYSROOT"
CFLAGS="$CFLAGS -I$SYSROOT/include"

echo "Compiling hello_new.c to LLVM bitcode..."
clang $CFLAGS --target=wasm32-wasi -emit-llvm -c hello_new.c -o hello_new.bc

# Check if compilation succeeded
if [ ! -f hello_new.bc ]; then
    echo "Error: Compilation failed! Bitcode file not created."
    exit 1
fi

echo "Converting to human-readable LLVM IR..."
llvm-dis hello_new.bc -o hello_new.ll

echo "Converting LLVM IR to WebAssembly object file..."
llc -march=wasm32 -filetype=obj hello_new.bc -o hello_new.o

# Check if object file was created
if [ ! -f hello_new.o ]; then
    echo "Error: Failed to create WebAssembly object file!"
    exit 1
fi

echo "Linking the object file to create WebAssembly module..."
# Get path to wasm-ld
WASM_LD="$WASI_SDK_PATH/bin/wasm-ld"
if [ ! -f "$WASM_LD" ]; then
    # Try to use system wasm-ld if WASI SDK's isn't available
    WASM_LD=$(which wasm-ld)
    if [ -z "$WASM_LD" ]; then
        echo "Error: wasm-ld not found!"
        exit 1
    fi
fi

# Link with WASI startup code and required libraries
$WASM_LD --export-all --no-entry \
    --allow-undefined \
    -L$SYSROOT/lib/wasm32-wasi \
    -lc \
    hello_new.o -o hello_new.wasm

# Check if wasm file was created
if [ ! -f hello_new.wasm ]; then
    echo "Error: Failed to create WebAssembly module!"
    exit 1
fi

# Generate text format if wasm2wat is available
if command -v wasm2wat &> /dev/null; then
    echo "Generating WebAssembly text format..."
    wasm2wat hello_new.wasm -o hello_new.wat
else
    echo "Warning: wasm2wat not found, skipping text format generation"
fi

echo "Compilation complete!"
echo "Generated files:"
ls -la hello_new.*

echo "Created HTML test file: hello_new_test.html"
echo ""
echo "To test the WebAssembly module, start a local server:"
echo "   python3 -m http.server"
echo "Then open http://localhost:8000/hello_new_test.html in your browser"