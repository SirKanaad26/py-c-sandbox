"""
Comparison of raw_uncompress_to_iovec functionality between test.py and main.py

This file compares the implementation and expected output of the raw_uncompress_to_iovec
function in both the test file (mock implementation) and main.py (actual WASM implementation).
"""

import sys
import os

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def compare_implementations():
    print("=" * 80)
    print("COMPARISON: raw_uncompress_to_iovec - test.py vs main.py")
    print("=" * 80)
    
    # Test data setup (same for both)
    test_data = b"hello world " * 10
    print(f"Test data: {test_data}")
    print(f"Test data length: {len(test_data)} bytes")
    
    # Buffer configuration (same for both)
    buffer_sizes = [40, 40, len(test_data) - 80]  # [40, 40, 40]
    print(f"Buffer sizes: {buffer_sizes}")
    print(f"Total buffer size: {sum(buffer_sizes)} bytes")
    print()
    
    # ==========================================
    # TEST.PY IMPLEMENTATION (MOCK)
    # ==========================================
    print("1. TEST.PY IMPLEMENTATION (Mock)")
    print("-" * 40)
    
    class MockSnappyWasm:
        def compress(self, data):
            # Mock compression - just return reversed data for testing
            return data[::-1]
        
        def raw_uncompress_to_iovec(self, compressed_data, buffer_sizes):
            """Mock implementation from test.py"""
            print(f"Would raw uncompress {len(compressed_data)} bytes using RawUncompressToIOVec to {len(buffer_sizes)} buffers")
            # For demo, return mock uncompressed data split into multiple buffers
            return [b"MOCK_BUFFER_1", b"MOCK_BUFFER_2", b"MOCK_BUFFER_3"][:len(buffer_sizes)]
    
    mock_snappy = MockSnappyWasm()
    mock_compressed = mock_snappy.compress(test_data)
    
    print(f"Mock compressed data: {mock_compressed[:50]}...")
    print(f"Mock compressed length: {len(mock_compressed)} bytes")
    
    try:
        mock_result = mock_snappy.raw_uncompress_to_iovec(mock_compressed, buffer_sizes)
        print(f"Mock result: {len(mock_result)} buffers")
        for i, buf in enumerate(mock_result):
            print(f"  Buffer {i}: {buf} ({len(buf)} bytes)")
        
        mock_reconstructed = b"".join(mock_result)
        print(f"Mock reconstructed: {mock_reconstructed}")
        print(f"Mock reconstructed length: {len(mock_reconstructed)} bytes")
        print(f"Mock integrity check: {'PASS' if test_data == mock_reconstructed else 'FAIL'}")
        
    except Exception as e:
        print(f"Mock implementation failed: {e}")
    
    print()
    
    # ==========================================
    # MAIN.PY IMPLEMENTATION (ACTUAL WASM)
    # ==========================================
    print("2. MAIN.PY IMPLEMENTATION (Actual WASM)")
    print("-" * 40)
    
    try:
        from snappywasm.core import SnappyWasm
        
        # Try to find WASM file
        wasm_path = None
        possible_paths = [
            "snappy.wasm",
            "rawUncompressToIOVec/snappy.wasm",
            "../snappy.wasm",
            "build/snappy.wasm"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                wasm_path = path
                break
        
        if not wasm_path:
            print("WASM file not found. Checked paths:")
            for path in possible_paths:
                print(f"  {path} - {'EXISTS' if os.path.exists(path) else 'NOT FOUND'}")
            print("\nSkipping actual WASM implementation test.")
            return
        
        print(f"Using WASM file: {wasm_path}")
        real_snappy = SnappyWasm(wasm_path)
        
        print(f"WASM Version: {real_snappy.get_version()}")
        
        # Real compression
        real_compressed = real_snappy.compress(test_data)
        print(f"Real compressed data: {real_compressed[:50]}...")
        print(f"Real compressed length: {len(real_compressed)} bytes")
        print(f"Compression ratio: {(1 - len(real_compressed)/len(test_data))*100:.1f}%")
        
        # Check if the method exists
        if hasattr(real_snappy, 'raw_uncompress_to_iovec'):
            try:
                real_result = real_snappy.raw_uncompress_to_iovec(real_compressed, buffer_sizes)
                print(f"Real result: {len(real_result)} buffers")
                for i, buf in enumerate(real_result):
                    print(f"  Buffer {i}: {buf} ({len(buf)} bytes)")
                
                real_reconstructed = b"".join(real_result)
                print(f"Real reconstructed: {real_reconstructed}")
                print(f"Real reconstructed length: {len(real_reconstructed)} bytes")
                print(f"Real integrity check: {'PASS' if test_data == real_reconstructed else 'FAIL'}")
                
            except RuntimeError as e:
                print(f"WASM function call failed: {e}")
                print("This might mean the WASM module doesn't include RawUncompressToIOVec")
            except Exception as e:
                print(f"Unexpected error in WASM implementation: {e}")
        else:
            print("raw_uncompress_to_iovec method not found in SnappyWasm class")
            print("Available methods:")
            methods = [method for method in dir(real_snappy) if not method.startswith('_')]
            for method in sorted(methods):
                print(f"  {method}")
    
    except ImportError as e:
        print(f"Failed to import SnappyWasm: {e}")
        print("This might mean the snappywasm module is not properly set up.")
    except Exception as e:
        print(f"WASM implementation failed: {e}")
    
    print()
    
    # ==========================================
    # COMPARISON SUMMARY
    # ==========================================
    print("3. COMPARISON SUMMARY")
    print("-" * 40)
    
    print("KEY DIFFERENCES:")
    print()
    
    print("test.py (Mock Implementation):")
    print("  ✓ Always returns fixed mock data: [b'MOCK_BUFFER_1', b'MOCK_BUFFER_2', b'MOCK_BUFFER_3']")
    print("  ✓ Doesn't actually compress or decompress")
    print("  ✓ Used for testing the interface without WASM")
    print("  ✓ Prints debug messages about what it 'would' do")
    print("  ✗ Doesn't validate buffer sizes")
    print("  ✗ Doesn't preserve data integrity")
    print()
    
    print("main.py (Real WASM Implementation):")
    print("  ✓ Actually compresses data using Snappy algorithm")
    print("  ✓ Actually decompresses using RawUncompressToIOVec WASM function")
    print("  ✓ Validates buffer sizes match expected uncompressed length")
    print("  ✓ Preserves data integrity (input == reconstructed output)")
    print("  ✓ Handles WASM memory management")
    print("  ✓ Returns actual decompressed data split into specified buffers")
    print("  ✗ Requires WASM file to be built and available")
    print("  ✗ More complex error handling for WASM-specific issues")
    print()
    
    print("EXPECTED BEHAVIOR:")
    print()
    print("Mock (test.py):")
    print("  Input:  b'hello world hello world ...' (120 bytes)")
    print("  Output: [b'MOCK_BUFFER_1', b'MOCK_BUFFER_2', b'MOCK_BUFFER_3']")
    print("  Result: Data integrity FAIL (mock data != original)")
    print()
    
    print("Real (main.py):")
    print("  Input:  b'hello world hello world ...' (120 bytes)")
    print("  Output: [first_40_bytes, next_40_bytes, last_40_bytes]")
    print("  Result: Data integrity PASS (reconstructed == original)")
    print()
    
    print("FUNCTION SIGNATURES:")
    print("  Both: raw_uncompress_to_iovec(compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]")
    print()
    
    print("USE CASES:")
    print("  test.py: Development, testing, mocking, interface validation")
    print("  main.py: Production, actual compression/decompression, performance testing")

def run_side_by_side_test():
    """Run both implementations side by side for direct comparison"""
    print("\n" + "=" * 80)
    print("SIDE-BY-SIDE EXECUTION")
    print("=" * 80)
    
    test_data = b"hello world " * 10
    buffer_sizes = [40, 40, 40]
    
    print(f"Input: {test_data}")
    print(f"Buffer sizes: {buffer_sizes}")
    print()
    
    # Mock version
    print("MOCK VERSION OUTPUT:")
    print("-" * 30)
    
    class MockSnappy:
        def compress(self, data): return data[::-1]
        def raw_uncompress_to_iovec(self, compressed, sizes):
            print(f"Would raw uncompress {len(compressed)} bytes using RawUncompressToIOVec to {len(sizes)} buffers")
            return [b"MOCK_BUFFER_1", b"MOCK_BUFFER_2", b"MOCK_BUFFER_3"][:len(sizes)]
    
    mock = MockSnappy()
    mock_compressed = mock.compress(test_data)
    mock_result = mock.raw_uncompress_to_iovec(mock_compressed, buffer_sizes)
    
    print(f"Compressed: {mock_compressed[:30]}... ({len(mock_compressed)} bytes)")
    print(f"Decompressed buffers: {len(mock_result)}")
    for i, buf in enumerate(mock_result):
        print(f"  [{i}]: {buf}")
    print(f"Reconstructed: {b''.join(mock_result)}")
    print(f"Integrity: {'PASS' if test_data == b''.join(mock_result) else 'FAIL'}")
    print()
    
    # Real version (if available)
    print("REAL VERSION OUTPUT:")
    print("-" * 30)
    
    try:
        # This would be the actual implementation
        print("(Would show actual WASM compression/decompression results)")
        print("(Requires WASM file and proper setup)")
        print("Example expected output:")
        print(f"Compressed: <actual_snappy_compressed_data> (~80-90 bytes)")
        print(f"Decompressed buffers: 3")
        print(f"  [0]: {test_data[:40]}")
        print(f"  [1]: {test_data[40:80]}")
        print(f"  [2]: {test_data[80:120]}")
        print(f"Reconstructed: {test_data}")
        print(f"Integrity: PASS")
        
    except Exception as e:
        print(f"Real version not available: {e}")

if __name__ == "__main__":
    compare_implementations()
    # run_side_by_side_test()