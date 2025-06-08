#!/usr/bin/env python3
"""
Simple example of calling CompressFromSourceToSink function from Snappy WASM module
"""

import wasmtime

def create_minimal_imports(store):
    """Create minimal required imports for the WASM module"""
    
    # WASI imports
    def fd_close(fd):
        return 0
    
    def fd_write(fd, iovs_ptr, iovs_len, nwritten_ptr):
        return 0
    
    def fd_seek(fd, offset, whence, newoffset_ptr): 
        return 0
    
    # Environment imports
    def emscripten_notify_memory_growth(index):
        pass
    
    # Create function types
    fd_close_type = wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    fd_write_type = wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32(), 
                                       wasmtime.ValType.i32(), wasmtime.ValType.i32()], 
                                      [wasmtime.ValType.i32()])
    fd_seek_type = wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i64(), 
                                      wasmtime.ValType.i32(), wasmtime.ValType.i32()], 
                                     [wasmtime.ValType.i32()])
    notify_type = wasmtime.FuncType([wasmtime.ValType.i32()], [])
    
    return [
        wasmtime.Func(store, notify_type, emscripten_notify_memory_growth),
        wasmtime.Func(store, fd_close_type, fd_close),
        wasmtime.Func(store, fd_write_type, fd_write),
        wasmtime.Func(store, fd_seek_type, fd_seek)
    ]

def compress_data_example():
    """Simple example of using CompressFromSourceToSink"""
    
    # Initialize WASM runtime
    engine = wasmtime.Engine()
    store = wasmtime.Store(engine)
    
    # Load the WASM module
    with open('snappy.wasm', 'rb') as f:
        wasm_bytes = f.read()
    
    module = wasmtime.Module(engine, wasm_bytes)
    
    # Create instance with required imports
    imports = create_minimal_imports(store)
    instance = wasmtime.Instance(store, module, imports)
    
    # Initialize module if needed
    initialize = instance.exports(store).get("_initialize")
    if initialize:
        initialize(store)
    
    # Get required functions
    exports = instance.exports(store)
    allocate_memory = exports["AllocateMemory"]
    free_memory = exports["FreeMemory"]
    write_to_memory = exports["WriteToMemory"]
    compress_source_to_sink = exports["CompressFromSourceToSink"]
    max_compressed_length = exports["MaxCompressedLength"]
    
    # Prepare test data
    test_string = "Hello, Snappy compression!"
    test_bytes = test_string.encode('utf-8')
    input_size = len(test_bytes)
    
    # Allocate memory for input
    input_ptr = allocate_memory(store, input_size)
    
    # Write data to WASM memory
    for i, byte in enumerate(test_bytes):
        write_to_memory(store, input_ptr + i, byte, 1)
    
    # Calculate maximum compressed size and allocate output buffer
    max_compressed_size = max_compressed_length(store, input_size)
    output_ptr = allocate_memory(store, max_compressed_size)
    
    # Call the compression function
    compressed_size = compress_source_to_sink(store, input_ptr, input_size, 
                                            output_ptr, max_compressed_size)
    
    if compressed_size > 0:
        print(f"✅ Compression successful!")
        print(f"   Original size: {input_size} bytes")
        print(f"   Compressed size: {compressed_size} bytes")
        print(f"   Compression ratio: {(1 - compressed_size/input_size)*100:.1f}%")
    else:
        print("❌ Compression failed")
    
    # Clean up memory
    free_memory(store, input_ptr)
    free_memory(store, output_ptr)

if __name__ == "__main__":
    compress_data_example()