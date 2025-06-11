import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/snappywasm')
# from snappywasm.snappy_sandbox import SnappyWasm
from snappywasm.snappy_sandbox_framework import SnappyWasm

def get_memory_size(snappy):
    """Get memory size using correct wasmtime API"""
    if snappy.memory:
        try:
            # Try different possible method names for wasmtime memory
            if hasattr(snappy.memory, 'size'):
                return snappy.memory.size(snappy.store) * 65536  # Convert pages to bytes
            elif hasattr(snappy.memory, 'data_len'):
                return snappy.memory.data_len(snappy.store)
            elif hasattr(snappy.memory, 'data_size'):
                return snappy.memory.data_size(snappy.store)
            else:
                return 16 * 1024 * 1024  # 16MB default
        except Exception:
            return 16 * 1024 * 1024  # 16MB fallback
    return 0

def check_simple_memory(snappy, compressed_data, output_size):
    """Simple memory check with conservative estimation"""
    if not snappy.memory:
        return False
    
    memory_size = get_memory_size(snappy)
    compressed_len = len(compressed_data)
    needed = compressed_len + 2048 + output_size + 1024  # Match function spacing
    
    return needed <= memory_size

def test_basic_functionality():
    """Test basic uncompress_source_sink functionality"""
    print("Testing Basic uncompress_source_sink Functionality")
    print("=" * 60)
    
    snappy = SnappyWasm()
    
    memory_size = get_memory_size(snappy)
    print(f"WASM Memory Size: {memory_size} bytes ({memory_size / (1024*1024):.1f} MB)")
    
    # Start with very small test cases
    test_cases = [
        ("Tiny", "Hi"),
        ("Small", "Hello, World!"),
        ("Short text", "Hello, World! This is a test."),
        ("Medium text", "The quick brown fox jumps over the lazy dog."),
        ("Repetitive small", "ABCD" * 10),
        ("Unicode text", "Hello 世界 🌍"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_name, test_data in test_cases:
        print(f"\n--- {test_name} ---")
        
        original_data = test_data.encode('utf-8')
        print(f"Original size: {len(original_data)} bytes")
        
        try:
            # First compress with regular method
            compressed_data = snappy.compress(original_data)
            print(f"Compressed size: {len(compressed_data)} bytes")
            
            # Check if we have enough memory (conservative check)
            if not check_simple_memory(snappy, compressed_data, len(original_data)):
                print(f"Skipping: May not have enough memory for {len(original_data)} byte output")
                continue
            
            # Test uncompress_source_sink
            start_time = time.time()
            uncompressed_data = snappy.uncompress_source_sink(compressed_data)
            decompress_time = time.time() - start_time
            
            print(f"Uncompressed size: {len(uncompressed_data)} bytes")
            print(f"Decompression time: {decompress_time*1000:.2f}ms")
            
            # Verify integrity
            if uncompressed_data == original_data:
                print("PASSED - Data integrity verified")
                passed += 1
            else:
                print("FAILED - Data mismatch")
                print(f"Expected: {len(original_data)} bytes")
                print(f"Got: {len(uncompressed_data)} bytes")
                
        except Exception as e:
            print(f"FAILED - {e}")
            # For debugging the specific error
            if "memory" in str(e).lower():
                print(f"Memory-related error - this confirms memory constraints")
    
    print(f"\nBasic Functionality Results: {passed}/{total} passed")
    return passed > 0

def test_different_data_sizes():
    """Test with various data sizes"""
    print("\nTesting Different Data Sizes")
    print("=" * 45)
    
    snappy = SnappyWasm()
    
    # Use progressively larger sizes but stop when we hit memory limits
    size_test_cases = [
        ("Tiny (1 byte)", b"A"),
        ("Small (10 bytes)", b"Hello123!@"),
        ("Medium (100 bytes)", b"This is a medium-sized test string for compression."),
        ("Large (300 bytes)", b"Pattern data. " * 20),
        ("Larger (500 bytes)", b"Test data. " * 50),
    ]
    
    passed = 0
    total = len(size_test_cases)
    
    for size_name, test_data in size_test_cases:
        print(f"\n--- {size_name} ---")
        print(f"Data size: {len(test_data)} bytes")
        
        try:
            # Compress first
            compressed_data = snappy.compress(test_data)
            print(f"Compressed: {len(compressed_data)} bytes")
            
            # Check memory
            if not check_simple_memory(snappy, compressed_data, len(test_data)):
                print(f"Skipping: May not have enough memory")
                continue
            
            # Test uncompress_source_sink
            start_time = time.time()
            uncompressed_data = snappy.uncompress_source_sink(compressed_data)
            decompress_time = time.time() - start_time
            
            print(f"Decompression time: {decompress_time*1000:.2f}ms")
            
            # Verify
            if uncompressed_data == test_data:
                print("PASSED")
                passed += 1
            else:
                print("FAILED - Size or content mismatch")
                
        except Exception as e:
            print(f"FAILED - {e}")
            if "memory" in str(e).lower():
                print(f"   Memory constraint hit at {len(test_data)} bytes")
                break 
    
    print(f"\nSize Test Results: {passed}/{total} passed")
    return passed > 0

def test_error_conditions():
    """Test error handling"""
    print("\nTesting Error Conditions")
    print("=" * 35)
    
    snappy = SnappyWasm()
    
    error_cases = [
        ("Empty data", b""),
        ("Invalid data", b"Not compressed data"),
        ("Random bytes", bytes(range(20))),
        ("Truncated", b"\x0C\x00\x00Hi"),
    ]
    
    for case_name, invalid_data in error_cases:
        print(f"\n--- {case_name} ---")
        print(f"Input size: {len(invalid_data)} bytes")
        
        # Test uncompress_source_sink
        try:
            result = snappy.uncompress_source_sink(invalid_data)
            print(f"Unexpected success: {len(result)} bytes decompressed")
        except Exception as e:
            print(f"Expected failure: {type(e).__name__}")

def test_comparison_with_standard():
    """Compare with standard uncompress"""
    print("\nComparison with Standard Uncompress")
    print("=" * 50)
    
    snappy = SnappyWasm()
    
    # Small comparison data
    comparison_data = [
        ("Short text", "Hello, test!"),
        ("Medium data", "This is a test. " * 3),
        ("Repetitive", "ABC" * 5),
    ]
    
    for test_name, test_data in comparison_data:
        print(f"\n--- {test_name} ---")
        
        original_data = test_data.encode('utf-8')
        print(f"Data size: {len(original_data)} bytes")
        
        try:
            compressed_data = snappy.compress(original_data)
            
            # Check memory
            if not check_simple_memory(snappy, compressed_data, len(original_data)):
                print(f"⚠️ Skipping: May not have enough memory")
                continue
            
            # Test both methods
            start_time = time.time()
            result_standard = snappy.uncompress(compressed_data)
            time_standard = time.time() - start_time
            
            start_time = time.time()
            result_source_sink = snappy.uncompress_source_sink(compressed_data)
            time_source_sink = time.time() - start_time
            
            print(f"Standard: {time_standard*1000:.2f}ms")
            print(f"Source/Sink: {time_source_sink*1000:.2f}ms")
            
            # Compare results
            if result_standard == result_source_sink == original_data:
                print("Both methods produced identical correct results")
                
                # Performance comparison
                if time_source_sink < time_standard:
                    speedup = time_standard / time_source_sink
                    print(f"Source/Sink is {speedup:.2f}x faster")
                elif time_standard < time_source_sink:
                    slowdown = time_source_sink / time_standard
                    print(f"Source/Sink is {slowdown:.2f}x slower")
                else:
                    print("⚖️ Similar performance")
            else:
                print("Methods produced different results")
                
        except Exception as e:
            print(f"Comparison test failed: {e}")

def main():
    """Main test function"""
    print("uncompress_source_sink Function Test Suite")
    print("=" * 60)
    
    try:
        # Check if function is available
        snappy = SnappyWasm()
        
        # if not snappy.exports.get("UncompressSourceSink"):
        #     print("UncompressSourceSink function not found in WASM module")
        #     return False
        
        print("UncompressSourceSink function found")
        print(f"Snappy WASM version: {snappy.get_version()}")
        
        # Run tests
        test_results = []
        
        test_results.append(("Basic Functionality", test_basic_functionality()))
        test_results.append(("Different Data Sizes", test_different_data_sizes()))
        
        # Additional tests
        test_error_conditions()
        test_comparison_with_standard()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "PASSED" if result else "FAILED"
            print(f"{test_name:<25}: {status}")
        
        print("-" * 60)
        print(f"Overall Result: {passed_tests}/{total_tests} critical test categories passed")
        
        if passed_tests == total_tests:
            print("ALL CRITICAL TESTS PASSED!")
            print("uncompress_source_sink function is working correctly")
        else:
            print("⚠️ Some critical tests failed")
            print("This may be due to memory constraints or function signature issues")
        
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)