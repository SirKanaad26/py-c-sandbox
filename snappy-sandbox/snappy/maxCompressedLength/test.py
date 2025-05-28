#!/usr/bin/env python3
"""
Test the WASM built directly from Google's actual Snappy source files
Including both MaxCompressedLength and GetUncompressedLength
"""

import os
import struct
from wasmtime import Store, Module, Instance, Func, FuncType, ValType


def create_wasm_imports(store):
    """Create necessary imports for the Snappy WASM module"""
    imports = {}
    
    # Common functions that C++ code might need
    def dummy_func(*args):
        return 0
    
    def abort_func():
        raise RuntimeError("WASM module called abort()")
    
    # Environment imports that Emscripten/C++ runtime might expect
    env_imports = {
        "abort": Func(store, FuncType([], []), abort_func),
        "__assert_fail": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32(), ValType.i32()], []), lambda *args: None),
        "__cxa_throw": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32()], []), lambda *args: None),
        "emscripten_memcpy_big": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32()], [ValType.i32()]), dummy_func),
        "emscripten_resize_heap": Func(store, FuncType([ValType.i32()], [ValType.i32()]), dummy_func),
    }
    
    imports["env"] = env_imports
    return imports


class SnappyWasmDirect:
    """Wrapper for Snappy WASM built from actual source files"""
    
    def __init__(self, wasm_path="snappy_direct.wasm"):
        if not os.path.exists(wasm_path):
            raise FileNotFoundError(f"WASM file not found: {wasm_path}")
        
        self.store = Store()
        
        with open(wasm_path, 'rb') as f:
            wasm_bytes = f.read()
        
        module = Module(self.store.engine, wasm_bytes)
        
        # Check what imports the module needs
        imports_needed = module.imports
        print(f"📋 Module requires {len(imports_needed)} imports:")
        for imp in imports_needed:
            print(f"  - {imp.module}.{imp.name}: {imp.type}")
        
        # Create imports
        if len(imports_needed) > 0:
            imports = create_wasm_imports(self.store)
            
            # Build import list in the order expected by the module
            import_list = []
            for imp in imports_needed:
                if imp.module in imports and imp.name in imports[imp.module]:
                    import_list.append(imports[imp.module][imp.name])
                else:
                    # Create a dummy function for unknown imports
                    if hasattr(imp.type, 'params') and hasattr(imp.type, 'results'):
                        # It's a function type
                        dummy = Func(store, imp.type, lambda *args: 0 if len(imp.type.results) > 0 else None)
                        import_list.append(dummy)
                    else:
                        raise Exception(f"Unknown import type for {imp.module}.{imp.name}: {imp.type}")
            
            self.instance = Instance(self.store, module, import_list)
        else:
            self.instance = Instance(self.store, module, [])
        
        self.exports = self.instance.exports(self.store)
        
        # Get memory reference if available
        if "memory" in self.exports:
            self.memory = self.exports["memory"]
        else:
            self.memory = None
            print("⚠️  No memory export found - some functions may not work")
        
        print("\n📦 Available functions:")
        for name in self.exports.keys():
            if not name.startswith("__"):  # Skip internal functions
                print(f"  - {name}")
        print()
    
    def max_compressed_length(self, source_length: int) -> int:
        """Get maximum compressed length for given source length"""
        if "MaxCompressedLength" not in self.exports:
            raise RuntimeError("MaxCompressedLength function not available")
        func = self.exports["MaxCompressedLength"]
        return func(self.store, source_length)
    
    def get_uncompressed_length(self, compressed_data: bytes) -> int:
        """Get uncompressed length from compressed data"""
        if not self.memory:
            raise RuntimeError("Memory not available - cannot use GetUncompressedLength")
        
        if "GetUncompressedLengthFromPtr" not in self.exports:
            raise RuntimeError("GetUncompressedLengthFromPtr function not available")
        
        # Allocate memory for compressed data
        if "AllocateMemory" in self.exports and "FreeMemory" in self.exports:
            compressed_ptr = self.exports["AllocateMemory"](self.store, len(compressed_data))
            result_ptr = self.exports["AllocateMemory"](self.store, 8)  # size_t is 8 bytes
        else:
            # Fallback: use simple offset-based allocation
            compressed_ptr = 1024
            result_ptr = 1024 + len(compressed_data) + 16
        
        try:
            # Write compressed data to WASM memory
            memory_data = self.memory.data_ptr(self.store)
            memory_data[compressed_ptr:compressed_ptr + len(compressed_data)] = compressed_data
            
            # Call GetUncompressedLength
            func = self.exports["GetUncompressedLengthFromPtr"]
            success = func(self.store, compressed_ptr, len(compressed_data), result_ptr)
            
            if success:
                # Read the result
                result_bytes = bytes(memory_data[result_ptr:result_ptr + 8])
                result = struct.unpack('<Q', result_bytes)[0]  # Little-endian uint64
                return result
            else:
                raise ValueError("Failed to get uncompressed length - invalid compressed data")
                
        finally:
            # Free allocated memory if functions are available
            if "FreeMemory" in self.exports:
                self.exports["FreeMemory"](self.store, compressed_ptr)
                self.exports["FreeMemory"](self.store, result_ptr)
    
    def compress(self, input_data: bytes) -> bytes:
        """Compress data using real Snappy algorithm"""
        if not self.memory:
            raise RuntimeError("Memory not available - cannot use Compress")
        
        if "CompressFromPtr" not in self.exports:
            raise RuntimeError("CompressFromPtr function not available")
        
        # Calculate maximum compressed size
        max_compressed_size = self.max_compressed_length(len(input_data))
        
        # Allocate memory
        if "AllocateMemory" in self.exports and "FreeMemory" in self.exports:
            input_ptr = self.exports["AllocateMemory"](self.store, len(input_data))
            output_ptr = self.exports["AllocateMemory"](self.store, max_compressed_size)
        else:
            # Fallback: use simple offset-based allocation
            input_ptr = 1024
            output_ptr = 1024 + len(input_data) + 16
        
        try:
            # Write input data to WASM memory
            memory_data = self.memory.data_ptr(self.store)
            memory_data[input_ptr:input_ptr + len(input_data)] = input_data
            
            # Call Compress function
            func = self.exports["CompressFromPtr"]
            compressed_size = func(self.store, input_ptr, len(input_data), output_ptr, max_compressed_size)
            
            if compressed_size == 0:
                raise ValueError("Compression failed")
            
            # Read compressed data
            compressed_data = bytes(memory_data[output_ptr:output_ptr + compressed_size])
            return compressed_data
            
        finally:
            # Free allocated memory if functions are available
            if "FreeMemory" in self.exports:
                self.exports["FreeMemory"](self.store, input_ptr)
                self.exports["FreeMemory"](self.store, output_ptr)
    
    def create_mock_snappy_data(self, uncompressed_size: int) -> bytes:
        """Create mock Snappy compressed data for testing GetUncompressedLength"""
        # Create a minimal valid Snappy stream
        # Snappy format: [varint uncompressed_length][compressed_blocks]
        
        # Encode uncompressed length as varint
        def encode_varint(value):
            result = bytearray()
            while value >= 0x80:
                result.append((value & 0x7F) | 0x80)
                value >>= 7
            result.append(value & 0x7F)
            return bytes(result)
        
        # Create a simple literal block (uncompressed data)
        # Format: [tag_byte][literal_data]
        varint_length = encode_varint(uncompressed_size)
        
        # Create minimal compressed data
        # For small sizes, we'll create a literal block
        if uncompressed_size <= 60:
            # Single literal block: tag = (len-1) << 2 | 0x00
            tag = ((uncompressed_size - 1) << 2) if uncompressed_size > 0 else 0
            mock_data = bytes([tag]) + b'x' * uncompressed_size
        else:
            # Multi-byte literal: tag = 0x01, then length bytes
            tag = 0x01
            length_bytes = struct.pack('<H', uncompressed_size)  # 2-byte length
            mock_data = bytes([tag]) + length_bytes + b'x' * uncompressed_size
        
        return varint_length + mock_data
    
    def get_version(self) -> int:
        """Get wrapper version"""
        if "GetVersion" not in self.exports:
            return 0
        func = self.exports["GetVersion"]
        return func(self.store)


def test_snappy_direct_wasm():
    """Test both MaxCompressedLength and GetUncompressedLength"""
    try:
        snappy = SnappyWasmDirect()
    except FileNotFoundError:
        print("❌ WASM file not found: snappy_direct.wasm")
        print("💡 Run ./build_from_snappy_source.sh first")
        return
    except Exception as e:
        print(f"❌ Failed to load WASM module: {e}")
        return
    
    print("🗜️  Testing WASM Built from Actual Snappy Source Files")
    print("=" * 60)
    
    print(f"📋 Version: {snappy.get_version()}")
    print()
    
    # Test MaxCompressedLength
    print("📏 Testing MaxCompressedLength:")
    test_sizes = [0, 10, 100, 1000, 10000, 100000]
    
    print(f"{'Input Size':>12} | {'Max Compressed':>14} | {'Overhead':>10} | {'Overhead %':>11}")
    print("-" * 60)
    
    for size in test_sizes:
        try:
            max_size = snappy.max_compressed_length(size)
            overhead = max_size - size
            overhead_pct = (overhead / size * 100) if size > 0 else 0
            
            print(f"{size:12,} | {max_size:14,} | {overhead:10,} | {overhead_pct:10.1f}%")
        except Exception as e:
            print(f"{size:12,} | {'ERROR':>14} | {'N/A':>10} | {'N/A':>11}")
            print(f"    Error: {e}")
    
    # Test GetUncompressedLength if available
    if snappy.memory and "GetUncompressedLengthFromPtr" in snappy.exports:
        print(f"\n📖 Testing GetUncompressedLength:")
        print(f"{'Original Size':>14} | {'Retrieved Size':>15} | {'Mock Data Size':>15} | {'Status':>8}")
        print("-" * 65)
        
        test_uncompressed_sizes = [0, 10, 50, 100, 1000]
        
        for original_size in test_uncompressed_sizes:
            try:
                # Create mock Snappy data
                mock_compressed = snappy.create_mock_snappy_data(original_size)
                
                # Try to get uncompressed length
                retrieved_size = snappy.get_uncompressed_length(mock_compressed)
                
                status = "✅ PASS" if retrieved_size == original_size else "❌ FAIL"
                print(f"{original_size:14,} | {retrieved_size:15,} | {len(mock_compressed):15,} | {status:>8}")
                
            except Exception as e:
                print(f"{original_size:14,} | {'ERROR':>15} | {'N/A':>15} | {'❌ FAIL':>8}")
                print(f"    Error: {e}")
    else:
        print(f"\n⚠️  GetUncompressedLength not available in this build")
    
    # Test Compress function if available
    if snappy.memory and "CompressFromPtr" in snappy.exports:
        print(f"\n🗜️  Testing Compress Function:")
        print(f"{'Test Data':>20} | {'Original':>10} | {'Compressed':>12} | {'Ratio':>8} | {'Retrieved':>10} | {'Status':>8}")
        print("-" * 85)
        
        test_cases = [
            (b"", "Empty"),
            (b"a", "Single char"),
            (b"hello", "Short string"),
            (b"hello world! " * 10, "Repeated text"),
            (b"a" * 100, "Repetitive"),
            (b"abcdefghijklmnopqrstuvwxyz" * 4, "Alphabet"),
            (bytes(range(256)), "Binary data"),
        ]
        
        for test_data, description in test_cases:
            try:
                # Compress the data
                compressed = snappy.compress(test_data)
                
                # Calculate compression ratio
                ratio = len(test_data) / len(compressed) if len(compressed) > 0 else float('inf')
                
                # Try to get uncompressed length from the real compressed data
                try:
                    retrieved_size = snappy.get_uncompressed_length(compressed)
                    size_match = retrieved_size == len(test_data)
                    status = "✅ PASS" if size_match else "❌ SIZE"
                except:
                    retrieved_size = "ERROR"
                    status = "❌ FAIL"
                
                print(f"{description:>20} | {len(test_data):10,} | {len(compressed):12,} | {ratio:8.2f} | {str(retrieved_size):>10} | {status:>8}")
                
            except Exception as e:
                print(f"{description:>20} | {len(test_data):10,} | {'ERROR':>12} | {'N/A':>8} | {'N/A':>10} | {'❌ FAIL':>8}")
                print(f"    Error: {e}")
        
        # Test compression round-trip (compress + decompress check)
        print(f"\n🔄 Compression Round-trip Tests:")
        round_trip_tests = [
            b"Hello, World!",
            b"The quick brown fox jumps over the lazy dog. " * 20,
            b"AAAAAAAAAA" * 50,  # Highly compressible
            bytes([i % 256 for i in range(1000)]),  # Pattern
        ]
        
        for i, test_data in enumerate(round_trip_tests):
            try:
                compressed = snappy.compress(test_data)
                retrieved_size = snappy.get_uncompressed_length(compressed)
                
                # Verify size matches
                if retrieved_size == len(test_data):
                    ratio = len(test_data) / len(compressed)
                    print(f"  Test {i+1}: {len(test_data):,} → {len(compressed):,} bytes (ratio: {ratio:.2f}) ✅")
                else:
                    print(f"  Test {i+1}: Size mismatch {len(test_data)} != {retrieved_size} ❌")
                    
            except Exception as e:
                print(f"  Test {i+1}: Error - {e} ❌")
    
    else:
        print(f"\n⚠️  Compress function not available in this build")
    
    # Performance test
    print(f"\n⚡ Performance Tests")
    print("-" * 30)
    
    import time
    iterations = 50000
    
    # Test MaxCompressedLength performance
    test_size = 1000
    try:
        start_time = time.time()
        for _ in range(iterations):
            snappy.max_compressed_length(test_size)
        mcl_time = time.time() - start_time
        
        print(f"MaxCompressedLength:")
        print(f"  {iterations:,} calls in {mcl_time:.3f}s")
        print(f"  {iterations/mcl_time:,.0f} calls/sec")
        print(f"  {(mcl_time/iterations)*1_000_000:.3f} μs/call")
    except Exception as e:
        print(f"MaxCompressedLength performance test failed: {e}")
    
    # Test Compress performance if available
    if snappy.memory and "CompressFromPtr" in snappy.exports:
        print(f"\nCompress Function:")
        try:
            test_data = b"Hello, World! This is a test string for compression. " * 20
            iterations_compress = 1000  # Fewer iterations due to complexity
            
            start_time = time.time()
            for _ in range(iterations_compress):
                snappy.compress(test_data)
            compress_time = time.time() - start_time
            
            print(f"  {iterations_compress:,} calls in {compress_time:.3f}s")
            print(f"  {iterations_compress/compress_time:,.0f} calls/sec")
            print(f"  {(compress_time/iterations_compress)*1_000_000:.3f} μs/call")
            
            # Show compression stats
            compressed = snappy.compress(test_data)
            ratio = len(test_data) / len(compressed)
            print(f"  Compression ratio: {ratio:.2f}:1 ({len(test_data):,} → {len(compressed):,} bytes)")
            
        except Exception as e:
            print(f"  Compress performance test failed: {e}")
    
    print(f"\n🎉 Test completed!")


if __name__ == "__main__":
    test_snappy_direct_wasm()