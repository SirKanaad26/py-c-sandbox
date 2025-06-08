import wasmtime
import os

def create_wasi_imports(store):
    """Create minimal WASI imports"""
    def fd_close(fd): return 0
    def fd_write(fd, iovs_ptr, iovs_len, nwritten_ptr): return 0
    def fd_seek(fd, offset, whence, newoffset_ptr): return 0
    
    fd_close_type = wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    fd_write_type = wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32(), wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    fd_seek_type = wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i64(), wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    
    return {
        'fd_close': wasmtime.Func(store, fd_close_type, fd_close),
        'fd_write': wasmtime.Func(store, fd_write_type, fd_write),
        'fd_seek': wasmtime.Func(store, fd_seek_type, fd_seek)
    }

def create_env_imports(store):
    
    def emscripten_notify_memory_growth(index): 
        pass

    notify_type = wasmtime.FuncType([wasmtime.ValType.i32()], [])
    return {
        'emscripten_notify_memory_growth': wasmtime.Func(store, notify_type, emscripten_notify_memory_growth)
    }

def write_data_to_memory(store, write_to_memory_func, ptr, data):
    for i, byte in enumerate(data):
        write_to_memory_func(store, ptr + i, byte, 1)

def test_uncompress_simple():
    wasm_file = 'snappywasm/wasm/snappy_direct.wasm'
    if not os.path.exists(wasm_file):
        print(f" WASM file not found: {wasm_file}")
        return False
    
    try:
        engine = wasmtime.Engine()
        store = wasmtime.Store(engine)
        
        with open(wasm_file, 'rb') as f:
            wasm_bytes = f.read()
        
        module = wasmtime.Module(engine, wasm_bytes)
        
        wasi_imports = create_wasi_imports(store)
        env_imports = create_env_imports(store)
        
        imports = [
            env_imports['emscripten_notify_memory_growth'],
            wasi_imports['fd_close'],
            wasi_imports['fd_write'],
            wasi_imports['fd_seek']
        ]
        
        instance = wasmtime.Instance(store, module, imports)
        print(" WASM module loaded successfully!")
        
        initialize = instance.exports(store).get("_initialize")
        if initialize:
            initialize(store)
        
        exports = instance.exports(store)
        get_version = exports["GetVersion"]
        allocate_memory = exports["AllocateMemory"]
        free_memory = exports["FreeMemory"]
        write_to_memory = exports["WriteToMemory"]
        compress_from_ptr = exports["CompressFromPtr"]
        uncompress_from_ptr = exports["UncompressFromPtr"]
        is_valid_compressed_buffer = exports["IsValidCompressedBuffer"]
        max_compressed_length = exports["MaxCompressedLength"]
        
        version = get_version(store)
        print(f"📋 WASM module version: {version}")
        
        if version < 5:
            print("Module version too old")
            return False
        
        test_cases = [
            (b"Hello, World!", "Short text"),
            (b"This is a longer test string for Snappy compression!", "Medium text"),
            (b"A" * 100, "Repetitive data (100 chars)"),
            (b"A" * 1000, "Repetitive data (1000 chars)"),
            (b"\x00\x01\x02\x03\x04\x05" * 50, "Binary pattern data"),
        ]
        
        all_passed = True
        
        for test_data, description in test_cases:
            print(f"\n🔍 Testing: {description} ({len(test_data)} bytes)")
            
            try:
                # Allocate and write input data
                input_size = len(test_data)
                input_ptr = allocate_memory(store, input_size)
                write_data_to_memory(store, write_to_memory, input_ptr, test_data)
                
                # Compress
                max_compressed_size = max_compressed_length(store, input_size)
                compressed_ptr = allocate_memory(store, max_compressed_size)
                compressed_size = compress_from_ptr(store, input_ptr, input_size, compressed_ptr, max_compressed_size)
                
                if compressed_size <= 0:
                    print(f"    Compression failed")
                    all_passed = False
                    continue
                
                print(f"    Compressed: {input_size} → {compressed_size} bytes")
                
                is_valid = is_valid_compressed_buffer(store, compressed_ptr, compressed_size)
                if is_valid != 1:
                    print(f"    Compressed data is invalid")
                    all_passed = False
                    continue
                
                print(f"    Compressed data is valid")
                
                uncompressed_ptr = allocate_memory(store, input_size)
                uncompressed_size = uncompress_from_ptr(store, compressed_ptr, compressed_size, uncompressed_ptr, input_size)
                
                if uncompressed_size <= 0:
                    print(f"    Decompression failed")
                    all_passed = False
                    continue
                
                print(f"    Decompressed: {compressed_size} → {uncompressed_size} bytes")
                
                if uncompressed_size == input_size:
                    print(f"    Size verification: PASSED")
                else:
                    print(f"    Size verification: FAILED (expected {input_size}, got {uncompressed_size})")
                    all_passed = False
                
                free_memory(store, input_ptr)
                free_memory(store, compressed_ptr)
                free_memory(store, uncompressed_ptr)
                
            except Exception as e:
                print(f"    Test failed: {e}")
                all_passed = False
        
        print(f"\nTesting Error Cases")
        
        garbage_data = b'\xFF\xFF\xFF\xFF\x00\x00\x00\x00'
        garbage_ptr = allocate_memory(store, len(garbage_data))
        write_data_to_memory(store, write_to_memory, garbage_ptr, garbage_data)
        
        is_valid_garbage = is_valid_compressed_buffer(store, garbage_ptr, len(garbage_data))
        print(f"   Invalid data validation: {' CORRECTLY INVALID' if is_valid_garbage == 0 else ' INCORRECTLY VALID'}")
        
        bad_output_ptr = allocate_memory(store, 100)
        bad_result = uncompress_from_ptr(store, garbage_ptr, len(garbage_data), bad_output_ptr, 100)
        print(f"   Invalid data decompression: {' CORRECTLY FAILED' if bad_result == 0 else ' INCORRECTLY SUCCEEDED'}")
        
        if is_valid_garbage != 0 or bad_result != 0:
            all_passed = False
        
        free_memory(store, garbage_ptr)
        free_memory(store, bad_output_ptr)
        
        print(f"\nTest Results:")
        if all_passed:
            print(f"   ALL TESTS PASSED")
            print(f"   Uncompress function is working correctly")
            print(f"   Tested compression → validation → decompression cycle")
            print(f"   Error detection working properly")
            return True
        else:
            print(f"    SOME TESTS FAILED")
            return False
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("STARTING UNCOMPRESS TEST")
    
    success = test_uncompress_simple()
    
    if success:
        print(" UNCOMPRESS TEST: SUCCESS")
        print(" Your Uncompress function is working!")
    else:
        print(" UNCOMPRESS TEST: FAILED")
