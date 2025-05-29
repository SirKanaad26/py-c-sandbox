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

# Use WASI_SDK_PATH if set
# if [ -n "$WASI_SDK_PATH" ]; then
echo "Using WASI SDK from: $WASI_SDK_PATH"
WASI_SYSROOT="$WASI_SDK_PATH/share/wasi-sysroot"
# fi

# Create a minimal temporary C file that includes the header and uses the defined functions
echo "// Auto-generated wrapper for $HEADER_FILE" > "$TEMP_C_FILE"
echo "#include \"$HEADER_FILE\"" >> "$TEMP_C_FILE"
echo "" >> "$TEMP_C_FILE"
echo "// Wrap the original function to avoid duplicate exports" >> "$TEMP_C_FILE"
echo "__attribute__((export_name(\"wasm_copy_array\")))" >> "$TEMP_C_FILE"
echo "void wasm_copy_array(int* dest, int* src, int len) {" >> "$TEMP_C_FILE"
echo "    copy_array(dest, src, len);" >> "$TEMP_C_FILE"
echo "}" >> "$TEMP_C_FILE"
echo "" >> "$TEMP_C_FILE"
echo "int main() {" >> "$TEMP_C_FILE"
echo "    int src[5] = {1, 2, 3, 4, 5};" >> "$TEMP_C_FILE"
echo "    int dest[5] = {0};" >> "$TEMP_C_FILE"
echo "    copy_array(dest, src, 5);" >> "$TEMP_C_FILE"
echo "    printf(\"Array copied: %d %d %d %d %d\\n\", dest[0], dest[1], dest[2], dest[3], dest[4]);" >> "$TEMP_C_FILE"
echo "    return 0;" >> "$TEMP_C_FILE"
echo "}" >> "$TEMP_C_FILE"

echo "Created temporary C file at: $TEMP_C_FILE"

# Compilation flags
if [ -n "$WASI_SYSROOT" ]; then
    echo "Using WASI sysroot: $WASI_SYSROOT"
    CFLAGS="--sysroot=$WASI_SYSROOT -I$WASI_SYSROOT/include -Wl,--export-all"
else
    echo "No WASI sysroot found, compilation will likely fail"
    echo "Please install WASI SDK and set WASI_SDK_PATH"
    CFLAGS=""
fi

echo "=== Compilation to WebAssembly ==="
echo "clang $CFLAGS --target=wasm32-wasi -o $OUTPUT_WASM $TEMP_C_FILE"
clang $CFLAGS --target=wasm32-wasi -o "$OUTPUT_WASM" "$TEMP_C_FILE"

if [ -f "$OUTPUT_WASM" ]; then
    echo "Success! Created $OUTPUT_WASM"

    # Generate text format from binary if wasm2wat is available
    if command -v wasm2wat &> /dev/null; then
        echo "Generating WebAssembly text format..."
        wasm2wat "$OUTPUT_WASM" -o "$OUTPUT_WAT"
        echo "Generated $OUTPUT_WAT"
    fi
    
    # If we have a wasm file, verify it and try to run it
    echo "WASM file created at: $OUTPUT_WASM"
    ls -la "$OUTPUT_WASM"
    
    if command -v wasmtime &> /dev/null; then
        echo "Running WebAssembly module with wasmtime:"
        echo "----------------------------------------"
        wasmtime "$OUTPUT_WASM" || echo "wasmtime execution failed (this may happen with WASI modules)"
        echo "----------------------------------------"
        
        # Check the functions available in the WASM file
        echo "Functions available in the WebAssembly module:"
        wasmtime --invoke wasm_copy_array "$OUTPUT_WASM" 2>&1 | grep -i "available exports" || echo "No function list available"
    fi
else
    echo "Failed to create WebAssembly module"
fi

# Clean up the temporary file unless --keep is specified
if [[ "$*" != *"--keep"* ]]; then
    rm -f "$TEMP_C_FILE" "$CURRENT_DIR/$OUTPUT_NAME.o"
    echo "Cleaned up temporary files"
else
    echo "Kept temporary files for inspection"
    echo "Temporary files kept: $TEMP_C_FILE"
fi

echo "Compilation of header file $HEADER_FILE complete!"
echo "WebAssembly file: $OUTPUT_WASM"