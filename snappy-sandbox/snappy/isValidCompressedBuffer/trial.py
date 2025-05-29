#!/usr/bin/env python3
"""
Test script for Snappy WASM module with proper imports
"""

import wasmtime

def create_wasi_imports(store):
    """Create minimal WASI imports"""
    
    # Dummy WASI functions - these won't actually be called in our use case
    def fd_close(fd):
        return 0  # Success
    
    def fd_write(fd, iovs_ptr, iovs_len, nwritten_ptr):
        return 0  # Success
    
    def fd_seek(fd, offset, whence, newoffset_ptr): 
        return 0  # Success
    
    # Create function types
    fd_close_type = wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    fd_write_type = wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32(), wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    fd_seek_type = wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i64(), wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
    
    # Create functions
    fd_close_func = wasmtime.Func(store, fd_close_type, fd_close)
    fd_write_func = wasmtime.Func(store, fd_write_type, fd_write)
    fd_seek_func = wasmtime.Func(store, fd_seek_type, fd_seek)
    
    return {
        'fd_close': fd_close_func,
        'fd_write': fd_write_func, 
        'fd_seek': fd_seek_func
    }

def create_env_imports(store):
    """Create environment imports"""
    
    def emscripten_notify_memory_growth(index):
        # Just a notification, nothing to do
        pass
    
    notify_type = wasmtime.FuncType([wasmtime.ValType.i32()], [])
    notify_func = wasmtime.Func(store, notify_type, emscripten_notify_memory_growth)
    
    return {
        'emscripten_notify_memory_growth': notify_func
    }

def test_snappy_validation():
    """Test the IsValidCompressedBuffer function in Snappy WASM module"""
    
    print("🧪 Testing Snappy WASM IsValidCompressedBuffer function...")
    
    try:
        engine = wasmtime.Engine()
        store = wasmtime.Store(engine)
        
        # Load the WASM file
        with open('snappy_direct.wasm', 'rb') as f:
            wasm_bytes = f.read()
        
        module = wasmtime.Module(engine, wasm_bytes)
        
        # Create required imports
        wasi_imports = create_wasi_imports(store)
        env_imports = create_env_imports(store)
        
        # Combine all imports in the order expected by the module
        imports = [
            env_imports['emscripten_notify_memory_growth'],  # env.emscripten_notify_memory_growth
            wasi_imports['fd_close'],                        # wasi_snapshot_preview1.fd_close
            wasi_imports['fd_write'],                        # wasi_snapshot_preview1.fd_write
            wasi_imports['fd_seek']                          # wasi_snapshot_preview1.fd_seek
        ]
        
        # Create instance with imports
        instance = wasmtime.Instance(store, module, imports)
        print("✅ WASM module loaded successfully with imports!")
        
        # Initialize the module
        initialize = instance.exports(store).get("_initialize")
        if initialize:
            initialize(store)
            print("✅ Module initialized")
        
        # Get the functions we need
        get_version = instance.exports(store)["GetVersion"]
        allocate_memory = instance.exports(store)["AllocateMemory"]
        free_memory = instance.exports(store)["FreeMemory"]
        write_to_memory = instance.exports(store)["WriteToMemory"]
        compress_from_ptr = instance.exports(store)["CompressFromPtr"]
        is_valid_compressed_buffer = instance.exports(store)["IsValidCompressedBuffer"]
        max_compressed_length = instance.exports(store)["MaxCompressedLength"]
        
        # Check version
        version = get_version(store)
        print(f"📋 WASM module version: {version}")
        
        if version < 4:
            print("❌ This module doesn't have IsValidCompressedBuffer function")
            return
        
        # Test data
        test_string = "Hello, Snappy WASM! This is a test string for compression and validation."
        test_bytes = test_string.encode('utf-8')
        
        print(f"📝 Test data: '{test_string}' ({len(test_bytes)} bytes)")
        
        # Allocate memory for input
        input_size = len(test_bytes)
        input_ptr = allocate_memory(store, input_size)
        print(f"📍 Allocated input memory at: {input_ptr}")
        
        # Write test data to WASM memory
        for i, byte in enumerate(test_bytes):
            write_to_memory(store, input_ptr + i, byte, 1)
        
        # Get maximum compressed size and allocate output buffer
        max_compressed_size = max_compressed_length(store, input_size)
        output_ptr = allocate_memory(store, max_compressed_size)
        print(f"📍 Allocated output memory at: {output_ptr} (max size: {max_compressed_size})")
        
        # Compress the data
        compressed_size = compress_from_ptr(store, input_ptr, input_size, output_ptr, max_compressed_size)
        
        if compressed_size > 0:
            print(f"✅ Compression successful! {input_size} bytes → {compressed_size} bytes")
            
            # Test 1: Validate the properly compressed buffer
            print("\n🔍 Test 1: Validating properly compressed data...")
            print(f"   Calling IsValidCompressedBuffer(ptr={output_ptr}, length={compressed_size})")
            is_valid = is_valid_compressed_buffer(store, output_ptr, compressed_size)
            print(f"   Raw return value: {is_valid}")
            print(f"   Result: {'✅ VALID' if is_valid == 1 else '❌ INVALID'}")
            
            # Test 2: Validate with wrong size (should be invalid)
            print("\n🔍 Test 2: Validating with wrong size...")
            print(f"   Calling IsValidCompressedBuffer(ptr={output_ptr}, length={compressed_size - 5})")
            is_valid_wrong_size = is_valid_compressed_buffer(store, output_ptr, compressed_size - 5)
            print(f"   Raw return value: {is_valid_wrong_size}")
            print(f"   Result: {'✅ VALID' if is_valid_wrong_size == 1 else '❌ INVALID'} (expected invalid)")
            
            # Test 3: Create some garbage data and test validation
            print("\n🔍 Test 3: Validating garbage data...")
            garbage_ptr = allocate_memory(store, 20)
            garbage_data = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13'
            for i, byte in enumerate(garbage_data):
                write_to_memory(store, garbage_ptr + i, byte, 1)
            
            print(f"   Calling IsValidCompressedBuffer(ptr={garbage_ptr}, length={len(garbage_data)})")
            is_valid_garbage = is_valid_compressed_buffer(store, garbage_ptr, len(garbage_data))
            print(f"   Raw return value: {is_valid_garbage}")
            print(f"   Result: {'✅ VALID' if is_valid_garbage == 1 else '❌ INVALID'} (expected invalid)")
            
            # Test 4: Test with zero-length data
            print("\n🔍 Test 4: Validating zero-length data...")
            print(f"   Calling IsValidCompressedBuffer(ptr={output_ptr}, length=0)")
            is_valid_empty = is_valid_compressed_buffer(store, output_ptr, 0)
            print(f"   Raw return value: {is_valid_empty}")
            print(f"   Result: {'✅ VALID' if is_valid_empty == 1 else '❌ INVALID'} (expected invalid)")
            
            # Cleanup
            free_memory(store, input_ptr)
            free_memory(store, output_ptr)
            free_memory(store, garbage_ptr)
            print("\n🧹 Memory cleaned up")
            
        else:
            print("❌ Compression failed!")
            free_memory(store, input_ptr)
            free_memory(store, output_ptr)
            return
        
        print("\n🎉 All tests completed!")
        print("\n📊 Summary:")
        print("   • Test 1 (valid compressed data): Should be VALID ✅")
        print("   • Test 2 (wrong size): Should be INVALID ❌") 
        print("   • Test 3 (garbage data): Should be INVALID ❌")
        print("   • Test 4 (zero length): Should be INVALID ❌")
        
    except FileNotFoundError:
        print("❌ snappy_direct.wasm not found! Make sure to build it first.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_snappy_validation()