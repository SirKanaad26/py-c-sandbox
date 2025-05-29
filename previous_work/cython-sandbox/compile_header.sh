#!/bin/bash

# Check if input file is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <header_file.h> [output_name]"
    exit 1
fi

# Use absolute paths to ensure files are created in the current directory
CURRENT_DIR="$(pwd)"
HEADER_FILE="$1"
OUTPUT_NAME="${2:-${HEADER_FILE%.h}}"
OUTPUT_WASM="$CURRENT_DIR/$OUTPUT_NAME.wasm"
OUTPUT_WAT="$CURRENT_DIR/$OUTPUT_NAME.wat"
TEMP_C_FILE="$CURRENT_DIR/_temp_${OUTPUT_NAME}.c"

echo "Working directory: $CURRENT_DIR"

echo "Checking for required tools..."
if ! command -v clang &> /dev/null; then
    echo "Error: clang not found. Please install LLVM/Clang."
    exit 1
fi

if ! command -v wasm-ld &> /dev/null; then
    echo "Error: wasm-ld not found. Please install LLVM."
    exit 1
fi

# Use WASI_SDK_PATH if set
if [ -n "$WASI_SDK_PATH" ]; then
    echo "Using WASI SDK from: $WASI_SDK_PATH"
    WASI_SYSROOT="$WASI_SDK_PATH/share/wasi-sysroot"
    
    if [ ! -d "$WASI_SYSROOT" ]; then
        echo "Warning: WASI sysroot not found at $WASI_SYSROOT"
    fi
else
    echo "WASI_SDK_PATH not set. Searching for WASI sysroot..."
    # Try to find WASI sysroot in known locations
    for WASI_PATH in "$CURRENT_DIR/wasi-sdk/share/wasi-sysroot" /opt/wasi-sdk/share/wasi-sysroot ~/wasi-sdk/wasi-sdk-*/share/wasi-sysroot /usr/local/share/wasi-sysroot; do
        if [ -d "$WASI_PATH" ]; then
            WASI_SYSROOT="$WASI_PATH"
            echo "Found WASI sysroot at: $WASI_SYSROOT"
            break
        fi
    done
fi

# Create a minimal temporary C file that just includes the header
echo "// Auto-generated wrapper for $HEADER_FILE" > "$TEMP_C_FILE"
echo "#include \"$HEADER_FILE\"" >> "$TEMP_C_FILE"
echo "int main() {" >> "$TEMP_C_FILE"
echo "    print_demo();" >> "$TEMP_C_FILE"
echo "    return 0;" >> "$TEMP_C_FILE"
echo "}" >> "$TEMP_C_FILE"

echo "Created temporary C file at: $TEMP_C_FILE"

# Compilation flags
if [ -n "$WASI_SYSROOT" ]; then
    echo "Using WASI sysroot: $WASI_SYSROOT"
    CFLAGS="--sysroot=$WASI_SYSROOT -I$WASI_SYSROOT/include"
else
    echo "No WASI sysroot found, compilation will likely fail"
    echo "Please install WASI SDK and set WASI_SDK_PATH"
    CFLAGS=""
fi

echo "=== Approach 1: Direct compilation to .wasm ==="
echo "clang $CFLAGS --target=wasm32-wasi -o $OUTPUT_WASM $TEMP_C_FILE"
clang $CFLAGS --target=wasm32-wasi -o "$OUTPUT_WASM" "$TEMP_C_FILE"

if [ -f "$OUTPUT_WASM" ]; then
    echo "Success! Created $OUTPUT_WASM"
else
    echo "Approach 1 failed. Trying approach 2..."
    
    echo "=== Approach 2: Two-step compilation via object file ==="
    echo "Step 1: Compile to object file"
    TEMP_O_FILE="$CURRENT_DIR/$OUTPUT_NAME.o"
    echo "clang $CFLAGS --target=wasm32-unknown-unknown -c $TEMP_C_FILE -o $TEMP_O_FILE"
    clang $CFLAGS --target=wasm32-unknown-unknown -c "$TEMP_C_FILE" -o "$TEMP_O_FILE"
    
    if [ -f "$TEMP_O_FILE" ]; then
        echo "Object file created successfully at: $TEMP_O_FILE"
        echo "Step 2: Linking with wasm-ld"
        echo "wasm-ld --export-all --no-entry --allow-undefined $TEMP_O_FILE -o $OUTPUT_WASM"
        wasm-ld --export-all --no-entry --allow-undefined "$TEMP_O_FILE" -o "$OUTPUT_WASM"
        
        if [ -f "$OUTPUT_WASM" ]; then
            echo "Success! Created $OUTPUT_WASM using two-step approach"
        else
            echo "Linking failed."
            echo "Trying with different wasm-ld options..."
            echo "wasm-ld --export-all --entry=main $TEMP_O_FILE -o $OUTPUT_WASM"
            wasm-ld --export-all --entry=main "$TEMP_O_FILE" -o "$OUTPUT_WASM"
            
            if [ -f "$OUTPUT_WASM" ]; then
                echo "Success! Created $OUTPUT_WASM with alternative linker options"
            else
                echo "All linking attempts failed"
            fi
        fi
    else
        echo "Failed to create object file."
    fi
fi

# If we have a wasm file, verify it and try to run it
if [ -f "$OUTPUT_WASM" ]; then
    echo "WASM file created at: $OUTPUT_WASM"
    ls -la "$OUTPUT_WASM"
    
    # Generate text format from binary if wasm2wat is available
    if command -v wasm2wat &> /dev/null; then
        echo "Generating WebAssembly text format..."
        wasm2wat "$OUTPUT_WASM" -o "$OUTPUT_WAT"
        echo "Generated $OUTPUT_WAT"
        ls -la "$OUTPUT_WAT"
    fi
    
    # Run with wasmtime if available
    if command -v wasmtime &> /dev/null; then
        echo "Running WebAssembly module with wasmtime:"
        echo "----------------------------------------"
        wasmtime "$OUTPUT_WASM" || echo "wasmtime execution failed"
        echo "----------------------------------------"
    else
        echo "wasmtime not found. Install with: brew install wasmtime"
    fi
else
    echo "Error: Failed to create WebAssembly module"
    echo "This is likely due to missing standard headers like stdio.h."
    echo "Please install WASI-SDK which provides these headers:"
    echo "  mkdir -p ~/wasi-sdk"
    echo "  cd ~/wasi-sdk"
    echo "  curl -LO https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-macos.tar.gz"
    echo "  tar xf wasi-sdk-20.0-macos.tar.gz"
    echo "  export WASI_SDK_PATH=~/wasi-sdk/wasi-sdk-20.0"
fi

# Clean up the temporary file unless --keep is specified
if [[ "$*" != *"--keep"* ]]; then
    rm -f "$TEMP_C_FILE" "$CURRENT_DIR/$OUTPUT_NAME.o"
    echo "Cleaned up temporary files"
else
    echo "Kept temporary files for inspection"
    echo "Temporary files kept: $TEMP_C_FILE $CURRENT_DIR/$OUTPUT_NAME.o"
fi

echo "Compilation of header file $HEADER_FILE complete!"
echo "Output files:"
ls -la "$OUTPUT_WASM" "$OUTPUT_WAT" 2>/dev/null
echo "Current directory contents:"
ls -la