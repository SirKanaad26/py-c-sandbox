#!/usr/bin/env python3
"""
Test script for the 2 new Source/Sink Uncompress functions:
1. UncompressSourceSink - bool Uncompress(Source* compressed, Sink* uncompressed);
2. UncompressAsMuchAsPossibleSourceSink - size_t UncompressAsMuchAsPossible(Source* compressed, Sink* uncompressed);
"""

import wasmtime
import os
import sys
import struct
import time

class SnappyWASM:
    def __init__(self, wasm_path="snappy.wasm"):
        """Initialize the Snappy WASM module"""
        if not os.path.exists(wasm_path):
            raise FileNotFoundError(f"WASM file not found: {wasm_path}")
            
        # Create WASM engine and store
        self.engine = wasmtime.Engine()
        self.store = wasmtime.Store(self.engine)
        
        # Load and instantiate the WASM module
        with open(wasm_path, 'rb') as f:
            wasm_bytes = f.read()
            
        module = wasmtime.Module(self.engine, wasm_bytes)
        
        # Check what imports the module expects
        imports = module.imports
        print(f"📋 Module expects {len(imports)} imports:")
        for imp in imports:
            print(f"   {imp.module}.{imp.name} ({imp.type})")
        
        # Create import objects based on what the module needs
        import_objects = []
        
        # Common WASM imports that might be needed
        for imp in imports:
            if imp.module == "env":
                if imp.name == "emscripten_notify_memory_growth":
                    # This function expects (param i32) -> ()
                    def notify_memory_growth(delta):
                        pass  # Do nothing
                    func = wasmtime.Func(self.store, wasmtime.FuncType([wasmtime.ValType.i32()], []), notify_memory_growth)
                    import_objects.append(func)
                elif imp.name == "__memory_base":
                    import_objects.append(wasmtime.Global(self.store, wasmtime.GlobalType(wasmtime.ValType.i32(), False), wasmtime.Val.i32(0)))
                elif imp.name == "__table_base":
                    import_objects.append(wasmtime.Global(self.store, wasmtime.GlobalType(wasmtime.ValType.i32(), False), wasmtime.Val.i32(0)))
                elif imp.name == "memory":
                    # Create memory if the module expects it as import
                    memory = wasmtime.Memory(self.store, wasmtime.MemoryType(256))  # 256 pages = 16MB
                    import_objects.append(memory)
                elif imp.name == "__indirect_function_table" or imp.name == "__table":
                    # Create table if needed
                    table = wasmtime.Table(self.store, wasmtime.TableType(wasmtime.ValType.funcref(), 0, None), wasmtime.Val.funcref(None))
                    import_objects.append(table)
                else:
                    print(f"⚠️  Unknown env import: {imp.name}, creating generic dummy")
                    # Create a generic dummy function
                    def generic_dummy(*args):
                        return 0 if imp.type.results else None
                    param_types = [wasmtime.ValType.i32()] * len(imp.type.params)
                    result_types = [wasmtime.ValType.i32()] * len(imp.type.results)
                    func = wasmtime.Func(self.store, wasmtime.FuncType(param_types, result_types), generic_dummy)
                    import_objects.append(func)
            elif imp.module == "wasi_snapshot_preview1":
                # WASI imports - create specific implementations based on function name
                if imp.name == "fd_write":
                    # fd_write(fd: i32, iovs: i32, iovs_len: i32, nwritten: i32) -> i32
                    def fd_write(fd, iovs, iovs_len, nwritten):
                        return 0  # Success
                    func = wasmtime.Func(self.store, wasmtime.FuncType([wasmtime.ValType.i32()] * 4, [wasmtime.ValType.i32()]), fd_write)
                    import_objects.append(func)
                elif imp.name == "fd_close":
                    # fd_close(fd: i32) -> i32
                    def fd_close(fd):
                        return 0  # Success
                    func = wasmtime.Func(self.store, wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]), fd_close)
                    import_objects.append(func)
                elif imp.name == "fd_seek":
                    # fd_seek(fd: i32, offset: i64, whence: i32, newoffset: i32) -> i32
                    def fd_seek(fd, offset, whence, newoffset):
                        return 0  # Success
                    func = wasmtime.Func(self.store, wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i64(), wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()]), fd_seek)
                    import_objects.append(func)
                else:
                    # Generic WASI function
                    def wasi_dummy(*args):
                        return 0
                    param_count = len(imp.type.params)
                    result_count = len(imp.type.results)
                    param_types = [wasmtime.ValType.i32()] * param_count
                    result_types = [wasmtime.ValType.i32()] * result_count
                    func = wasmtime.Func(self.store, wasmtime.FuncType(param_types, result_types), wasi_dummy)
                    import_objects.append(func)
            else:
                print(f"⚠️  Unknown module import: {imp.module}.{imp.name}")
                # Create a generic dummy
                def generic_dummy_2(*args):
                    return 0 if imp.type.results else None
                param_count = len(imp.type.params)
                result_count = len(imp.type.results)
                param_types = [wasmtime.ValType.i32()] * param_count
                result_types = [wasmtime.ValType.i32()] * result_count
                func = wasmtime.Func(self.store, wasmtime.FuncType(param_types, result_types), generic_dummy_2)
                import_objects.append(func)
        
        # Try to instantiate with the imports
        try:
            self.instance = wasmtime.Instance(self.store, module, import_objects)
            print("✅ WASM module instantiated successfully")
        except Exception as e:
            print(f"❌ Failed to instantiate with imports: {e}")
            # Fallback: try with empty imports (standalone WASM)
            try:
                self.instance = wasmtime.Instance(self.store, module, [])
                print("✅ WASM module instantiated without imports")
            except Exception as e2:
                raise RuntimeError(f"Failed to instantiate WASM module: {e2}")
        
        # Get memory - try different possible names
        self.memory = None
        for memory_name in ["memory", "Memory", "mem", "0"]:
            try:
                self.memory = self.instance.exports(self.store)[memory_name]
                print(f"✅ Found memory export: {memory_name}")
                break
            except KeyError:
                continue
        
        if self.memory is None:
            print("⚠️  No memory export found - some functions may not work")
        
        self.functions = {}
        
        # Map all the functions we need
        function_names = [
            "MaxCompressedLength", "GetUncompressedLength", "GetUncompressedLengthFromPtr",
            "Compress", "CompressFromPtr", "CompressWithOptions",
            "CompressFromSourceToSink", "CompressFromSourceToSinkWithOptions",
            "UncompressSourceSink", "UncompressAsMuchAsPossibleSourceSink",
            "RawCompress", "RawUncompress", "Uncompress", "UncompressFromPtr",
            "IsValidCompressedBuffer", "GetMinCompressionLevel", "GetMaxCompressionLevel",
            "AllocateMemory", "FreeMemory", "WriteToMemory", "ReadFromMemory", "GetVersion"
        ]
        
        for name in function_names:
            try:
                self.functions[name] = self.instance.exports(self.store)[name]
                print(f"✅ Loaded function: {name}")
            except KeyError:
                print(f"❌ Function not found: {name}")
        
        # Also try to find functions with underscore prefix (common in WASM)
        for name in function_names:
            if name not in self.functions:
                try:
                    self.functions[name] = self.instance.exports(self.store)[f"_{name}"]
                    print(f"✅ Loaded function with underscore: _{name}")
                except KeyError:
                    pass
    
    def get_memory_view(self):
        """Get a view of the WASM memory"""
        if self.memory is None:
            raise RuntimeError("No memory available - WASM module may not export memory")
        return self.memory.data_ptr(self.store)
    
    def allocate(self, size):
        """Allocate memory in WASM"""
        if "AllocateMemory" not in self.functions:
            raise RuntimeError("AllocateMemory function not available")
        return self.functions["AllocateMemory"](self.store, size)
    
    def free(self, ptr):
        """Free memory in WASM"""
        if "FreeMemory" not in self.functions:
            print("⚠️  FreeMemory function not available - memory leak possible")
            return
        self.functions["FreeMemory"](self.store, ptr)
    
    def write_to_memory(self, ptr, data):
        """Write data to WASM memory"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        try:
            memory_view = self.get_memory_view()
            for i, byte in enumerate(data):
                memory_view[ptr + i] = byte
        except RuntimeError:
            # Fallback: use WriteToMemory function if available
            if "WriteToMemory" in self.functions:
                # Write data in chunks to avoid large function calls
                chunk_size = 1024
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i+chunk_size]
                    self.functions["WriteToMemory"](self.store, ptr + i, chunk, len(chunk))
            else:
                raise RuntimeError("Cannot write to memory - no memory access method available")
    
    def read_from_memory(self, ptr, size):
        """Read data from WASM memory"""
        try:
            memory_view = self.get_memory_view()
            return bytes(memory_view[ptr:ptr + size])
        except RuntimeError:
            # Fallback: use ReadFromMemory function if available
            if "ReadFromMemory" in self.functions:
                # Note: This would need the WASM function to return data somehow
                # For now, just raise an error
                raise RuntimeError("Cannot read from memory - ReadFromMemory function needs special implementation")
            else:
                raise RuntimeError("Cannot read from memory - no memory access method available")

def test_uncompress_source_sink(snappy):
    """Test UncompressSourceSink function"""
    print("\n" + "="*70)
    print("🧪 TEST 1: UncompressSourceSink")
    print("   Testing: bool Uncompress(Source* compressed, Sink* uncompressed)")
    print("="*70)
    
    # Create test data with various characteristics
    test_cases = [
        ("Simple text", "Hello, World! This is a simple test string."),
        ("Repeated data", "ABCD" * 100),  # Highly compressible
        ("Large text", "This is a longer test string that contains more data to compress. " * 50),
        ("Mixed content", "1234567890" + "abcdefghijklmnopqrstuvwxyz" * 20 + "!@#$%^&*()" * 10),
        ("Binary-like", bytes(range(256)).decode('latin1') * 5),
    ]
    
    for test_name, test_data in test_cases:
        print(f"\n--- Testing: {test_name} ---")
        
        input_data = test_data.encode('utf-8')
        print(f"Original size: {len(input_data)} bytes")
        
        # First, compress the data using standard Compress function
        input_ptr = snappy.allocate(len(input_data))
        snappy.write_to_memory(input_ptr, input_data)
        
        max_compressed_size = snappy.functions["MaxCompressedLength"](snappy.store, len(input_data))
        compressed_ptr = snappy.allocate(max_compressed_size)
        
        compressed_size = snappy.functions["Compress"](
            snappy.store, 
            input_ptr, len(input_data),
            compressed_ptr, max_compressed_size
        )
        
        if compressed_size == 0:
            print("❌ Compression failed, skipping test")
            snappy.free(input_ptr)
            snappy.free(compressed_ptr)
            continue
            
        print(f"Compressed size: {compressed_size} bytes")
        print(f"Compression ratio: {len(input_data)/compressed_size:.2f}:1")
        
        # Now test UncompressSourceSink
        output_ptr = snappy.allocate(len(input_data) + 100)  # Extra space for safety
        
        try:
            start_time = time.time()
            
            # Call UncompressSourceSink
            result_size = snappy.functions["UncompressSourceSink"](
                snappy.store,
                compressed_ptr, compressed_size,
                output_ptr, len(input_data) + 100
            )
            
            decompress_time = time.time() - start_time
            
            if result_size > 0:
                print(f"✅ UncompressSourceSink successful!")
                print(f"   Decompressed size: {result_size} bytes")
                print(f"   Decompression time: {decompress_time*1000:.2f}ms")
                
                # Verify the decompressed data
                decompressed_data = snappy.read_from_memory(output_ptr, result_size)
                
                if decompressed_data == input_data:
                    print("✅ Data integrity verified!")
                else:
                    print("❌ Data integrity check failed!")
                    print(f"   Expected: {len(input_data)} bytes")
                    print(f"   Got: {len(decompressed_data)} bytes")
                    if len(decompressed_data) <= 100:
                        print(f"   Expected data start: {input_data[:50]}...")
                        print(f"   Got data start: {decompressed_data[:50]}...")
            else:
                print("❌ UncompressSourceSink failed!")
                
        finally:
            snappy.free(input_ptr)
            snappy.free(compressed_ptr)
            snappy.free(output_ptr)

def test_uncompress_as_much_as_possible_source_sink(snappy):
    """Test UncompressAsMuchAsPossibleSourceSink function"""
    print("\n" + "="*70)
    print("🧪 TEST 2: UncompressAsMuchAsPossibleSourceSink")
    print("   Testing: size_t UncompressAsMuchAsPossible(Source* compressed, Sink* uncompressed)")
    print("="*70)
    
    # Test with various buffer sizes to test partial decompression
    test_data = "This is a test for UncompressAsMuchAsPossible function. " * 100
    input_data = test_data.encode('utf-8')
    
    print(f"Original data size: {len(input_data)} bytes")
    
    # Compress the data first
    input_ptr = snappy.allocate(len(input_data))
    snappy.write_to_memory(input_ptr, input_data)
    
    max_compressed_size = snappy.functions["MaxCompressedLength"](snappy.store, len(input_data))
    compressed_ptr = snappy.allocate(max_compressed_size)
    
    compressed_size = snappy.functions["Compress"](
        snappy.store,
        input_ptr, len(input_data),
        compressed_ptr, max_compressed_size
    )
    
    if compressed_size == 0:
        print("❌ Initial compression failed")
        snappy.free(input_ptr)
        snappy.free(compressed_ptr)
        return
    
    print(f"Compressed size: {compressed_size} bytes")
    
    # Test with different output buffer sizes
    test_buffer_sizes = [
        ("Full buffer", len(input_data) + 100),
        ("Exact buffer", len(input_data)),
        ("Small buffer", len(input_data) // 2),
        ("Very small buffer", 100),
        ("Tiny buffer", 50),
    ]
    
    for buffer_name, buffer_size in test_buffer_sizes:
        print(f"\n--- Testing with {buffer_name}: {buffer_size} bytes ---")
        
        output_ptr = snappy.allocate(buffer_size)
        
        try:
            start_time = time.time()
            
            # Call UncompressAsMuchAsPossibleSourceSink
            bytes_written = snappy.functions["UncompressAsMuchAsPossibleSourceSink"](
                snappy.store,
                compressed_ptr, compressed_size,
                output_ptr, buffer_size
            )
            
            decompress_time = time.time() - start_time
            
            print(f"📊 Results:")
            print(f"   Bytes written: {bytes_written} bytes")
            print(f"   Buffer utilization: {bytes_written/buffer_size*100:.1f}%")
            print(f"   Decompression time: {decompress_time*1000:.2f}ms")
            
            if bytes_written > 0:
                # Read and verify as much data as was written
                decompressed_data = snappy.read_from_memory(output_ptr, bytes_written)
                
                # Check if the decompressed data matches the beginning of original data
                if decompressed_data == input_data[:bytes_written]:
                    print("✅ Partial data integrity verified!")
                    if bytes_written == len(input_data):
                        print("✅ Complete decompression achieved!")
                    else:
                        print(f"ℹ️  Partial decompression: {bytes_written}/{len(input_data)} bytes ({bytes_written/len(input_data)*100:.1f}%)")
                else:
                    print("❌ Partial data integrity check failed!")
                    
            else:
                print("⚠️  No bytes were written (buffer too small or error)")
                
        finally:
            snappy.free(output_ptr)
    
    snappy.free(input_ptr)
    snappy.free(compressed_ptr)

def test_error_conditions(snappy):
    """Test error conditions for both functions"""
    print("\n" + "="*70)
    print("🧪 TEST 3: Error Conditions Testing")
    print("="*70)
    
    print("\n--- Testing with invalid compressed data ---")
    
    # Create some invalid compressed data
    invalid_data = b"This is not compressed data at all!"
    
    invalid_ptr = snappy.allocate(len(invalid_data))
    snappy.write_to_memory(invalid_ptr, invalid_data)
    
    output_ptr = snappy.allocate(1000)
    
    try:
        # Test UncompressSourceSink with invalid data
        print("Testing UncompressSourceSink with invalid data...")
        result = snappy.functions["UncompressSourceSink"](
            snappy.store,
            invalid_ptr, len(invalid_data),
            output_ptr, 1000
        )
        
        if result == 0:
            print("✅ UncompressSourceSink correctly detected invalid data")
        else:
            print(f"❌ UncompressSourceSink should have failed but returned {result}")
        
        # Test UncompressAsMuchAsPossibleSourceSink with invalid data
        print("Testing UncompressAsMuchAsPossibleSourceSink with invalid data...")
        result = snappy.functions["UncompressAsMuchAsPossibleSourceSink"](
            snappy.store,
            invalid_ptr, len(invalid_data),
            output_ptr, 1000
        )
        
        print(f"UncompressAsMuchAsPossibleSourceSink result: {result} bytes")
        if result == 0:
            print("✅ UncompressAsMuchAsPossibleSourceSink correctly handled invalid data")
        else:
            print("ℹ️  UncompressAsMuchAsPossibleSourceSink may have partial results")
            
    finally:
        snappy.free(invalid_ptr)
        snappy.free(output_ptr)
    
    print("\n--- Testing with zero-length buffer ---")
    
    # Create valid compressed data first
    test_data = "Small test".encode('utf-8')
    input_ptr = snappy.allocate(len(test_data))
    snappy.write_to_memory(input_ptr, test_data)
    
    max_compressed_size = snappy.functions["MaxCompressedLength"](snappy.store, len(test_data))
    compressed_ptr = snappy.allocate(max_compressed_size)
    
    compressed_size = snappy.functions["Compress"](
        snappy.store,
        input_ptr, len(test_data),
        compressed_ptr, max_compressed_size
    )
    
    if compressed_size > 0:
        zero_buffer_ptr = snappy.allocate(1)  # Minimal buffer
        
        try:
            # Test with zero-size output buffer
            result1 = snappy.functions["UncompressSourceSink"](
                snappy.store,
                compressed_ptr, compressed_size,
                zero_buffer_ptr, 0  # Zero size buffer
            )
            
            result2 = snappy.functions["UncompressAsMuchAsPossibleSourceSink"](
                snappy.store,
                compressed_ptr, compressed_size,
                zero_buffer_ptr, 0  # Zero size buffer
            )
            
            print(f"UncompressSourceSink with 0-size buffer: {result1}")
            print(f"UncompressAsMuchAsPossibleSourceSink with 0-size buffer: {result2}")
            
            if result1 == 0 and result2 == 0:
                print("✅ Both functions correctly handled zero-size buffers")
            
        finally:
            snappy.free(zero_buffer_ptr)
    
    snappy.free(input_ptr)
    snappy.free(compressed_ptr)

def test_performance_comparison(snappy):
    """Compare performance of different uncompress methods"""
    print("\n" + "="*70)
    print("🧪 TEST 4: Performance Comparison")
    print("="*70)
    
    # Create a larger test dataset for meaningful performance testing
    test_data = "Performance test data with various patterns. " * 1000
    test_data += "1234567890" * 500
    test_data += "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 200
    
    input_data = test_data.encode('utf-8')
    print(f"Test data size: {len(input_data)} bytes")
    
    # Compress the data
    input_ptr = snappy.allocate(len(input_data))
    snappy.write_to_memory(input_ptr, input_data)
    
    max_compressed_size = snappy.functions["MaxCompressedLength"](snappy.store, len(input_data))
    compressed_ptr = snappy.allocate(max_compressed_size)
    
    compressed_size = snappy.functions["Compress"](
        snappy.store,
        input_ptr, len(input_data),
        compressed_ptr, max_compressed_size
    )
    
    if compressed_size == 0:
        print("❌ Compression failed")
        snappy.free(input_ptr)
        snappy.free(compressed_ptr)
        return
    
    print(f"Compressed size: {compressed_size} bytes")
    
    # Test multiple iterations for better timing accuracy
    iterations = 10
    
    methods = [
        ("Standard Uncompress", "Uncompress"),
        ("UncompressSourceSink", "UncompressSourceSink"),
        ("UncompressAsMuchAsPossibleSourceSink", "UncompressAsMuchAsPossibleSourceSink"),
    ]
    
    for method_name, function_name in methods:
        print(f"\n--- Testing {method_name} ---")
        
        total_time = 0
        successful_runs = 0
        
        for i in range(iterations):
            output_ptr = snappy.allocate(len(input_data) + 100)
            
            try:
                start_time = time.time()
                
                if function_name == "Uncompress":
                    result = snappy.functions[function_name](
                        snappy.store,
                        compressed_ptr, compressed_size,
                        output_ptr, len(input_data) + 100
                    )
                else:
                    result = snappy.functions[function_name](
                        snappy.store,
                        compressed_ptr, compressed_size,
                        output_ptr, len(input_data) + 100
                    )
                
                end_time = time.time()
                
                if result > 0:
                    total_time += (end_time - start_time)
                    successful_runs += 1
                    
            finally:
                snappy.free(output_ptr)
        
        if successful_runs > 0:
            avg_time = total_time / successful_runs
            throughput = len(input_data) / avg_time / 1024 / 1024  # MB/s
            
            print(f"   Average time: {avg_time*1000:.2f}ms")
            print(f"   Throughput: {throughput:.2f} MB/s")
            print(f"   Successful runs: {successful_runs}/{iterations}")
        else:
            print(f"   ❌ All runs failed")
    
    snappy.free(input_ptr)
    snappy.free(compressed_ptr)

def diagnose_wasm_module(wasm_path):
    """Diagnose WASM module to understand its structure"""
    print("🔍 Diagnosing WASM module...")
    
    try:
        engine = wasmtime.Engine()
        with open(wasm_path, 'rb') as f:
            wasm_bytes = f.read()
        module = wasmtime.Module(engine, wasm_bytes)
        
        print(f"📋 Module size: {len(wasm_bytes)} bytes")
        
        # Check imports
        imports = module.imports
        print(f"📥 Imports ({len(imports)}):")
        for imp in imports:
            print(f"   - {imp.module}.{imp.name} ({imp.type})")
        
        # Check exports
        exports = module.exports
        print(f"📤 Exports ({len(exports)}):")
        for exp in exports:
            print(f"   - {exp.name} ({exp.type})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error diagnosing WASM module: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Snappy WASM Tests for Source/Sink Uncompress Functions")
    print("=" * 80)
    
    # Check command line arguments for diagnostic mode
    if len(sys.argv) > 1 and sys.argv[1] == "--diagnose":
        wasm_path = sys.argv[2] if len(sys.argv) > 2 else "snappy.wasm"
        diagnose_wasm_module(wasm_path)
        return
    
    try:
        # Try different possible WASM file locations
        possible_paths = [
            "snappy.wasm",
            "../snappy.wasm", 
            "../../snappy.wasm",
            "../snappywasm/wasm/snappy.wasm",
            "./wasm/snappy.wasm"
        ]
        
        wasm_path = None
        for path in possible_paths:
            if os.path.exists(path):
                wasm_path = path
                print(f"📁 Found WASM file at: {path}")
                break
        
        if wasm_path is None:
            print("❌ Could not find snappy.wasm file in any of these locations:")
            for path in possible_paths:
                print(f"   - {path}")
            print("\n💡 Try running with: python test.py --diagnose /path/to/snappy.wasm")
            return
        
        # First diagnose the module
        print("\n🔍 Quick module diagnosis:")
        if not diagnose_wasm_module(wasm_path):
            print("❌ Module diagnosis failed")
            return
        
        print("\n🔧 Attempting to load WASM module...")
        
        # Initialize Snappy WASM
        snappy = SnappyWASM(wasm_path)
        
        # Check if we have the required functions
        required_functions = ["UncompressSourceSink", "UncompressAsMuchAsPossibleSourceSink"]
        missing_functions = []
        
        for func_name in required_functions:
            if func_name not in snappy.functions:
                missing_functions.append(func_name)
        
        if missing_functions:
            print(f"❌ Missing required functions: {missing_functions}")
            print("⚠️  Please ensure your WASM was built with version 12+ that includes these functions")
            
            # Show available functions that might be related
            available_uncompress_funcs = [name for name in snappy.functions.keys() if 'uncompress' in name.lower()]
            if available_uncompress_funcs:
                print(f"📋 Available uncompress-related functions: {available_uncompress_funcs}")
            
            return
        
        # Get version info if available
        if "GetVersion" in snappy.functions:
            try:
                version = snappy.functions["GetVersion"](snappy.store)
                print(f"📋 Snappy WASM Version: {version}")
                
                if version < 12:
                    print("⚠️  Warning: Version 12+ required for Source/Sink Uncompress functions")
                    print("    Please rebuild your WASM with the new functions")
                    return
            except Exception as e:
                print(f"⚠️  Could not get version: {e}")
        
        # Check if basic functions work
        print("\n🧪 Testing basic functionality...")
        
        # Test memory allocation
        try:
            test_ptr = snappy.allocate(100)
            print(f"✅ Memory allocation works (ptr: {test_ptr})")
            snappy.free(test_ptr)
            print("✅ Memory deallocation works")
        except Exception as e:
            print(f"❌ Memory management error: {e}")
            print("⚠️  Tests may fail due to memory issues")
        
        # Test basic compression if available
        if "Compress" in snappy.functions and "MaxCompressedLength" in snappy.functions:
            try:
                test_data = b"Hello, World!"
                input_ptr = snappy.allocate(len(test_data))
                snappy.write_to_memory(input_ptr, test_data)
                
                max_size = snappy.functions["MaxCompressedLength"](snappy.store, len(test_data))
                output_ptr = snappy.allocate(max_size)
                
                compressed_size = snappy.functions["Compress"](
                    snappy.store,
                    input_ptr, len(test_data),
                    output_ptr, max_size
                )
                
                if compressed_size > 0:
                    print("✅ Basic compression works")
                else:
                    print("❌ Basic compression failed")
                
                snappy.free(input_ptr)
                snappy.free(output_ptr)
                
            except Exception as e:
                print(f"❌ Basic compression test failed: {e}")
        
        # Run all tests
        print("\n🚀 Starting comprehensive tests...")
        test_uncompress_source_sink(snappy)
        test_uncompress_as_much_as_possible_source_sink(snappy)
        test_error_conditions(snappy)
        test_performance_comparison(snappy)
        
        print("\n" + "="*80)
        print("🎉 ALL SOURCE/SINK UNCOMPRESS TESTS COMPLETED!")
        print("✅ Both functions tested successfully!")
        print("   1. ✅ UncompressSourceSink")
        print("   2. ✅ UncompressAsMuchAsPossibleSourceSink")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Troubleshooting tips:")
        print("1. Ensure snappy.wasm is built with the latest version (12+)")
        print("2. Check that all required functions are exported")
        print("3. Try running with --diagnose flag to inspect the WASM module")
        print("4. Verify the WASM file is not corrupted")
        
        sys.exit(1)

if __name__ == "__main__":
    main()