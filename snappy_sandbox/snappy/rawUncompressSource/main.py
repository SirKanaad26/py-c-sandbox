import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def test_raw_uncompress():
    snappy = SnappyWasm()
    
    print("=== Snappy WASM RawUncompress Test ===\n")
    
    # Test data
    test_cases = [
        {
            "name": "Simple text",
            "data": b"Hello, World! This is a test string for Snappy compression.",
            "description": "Basic ASCII text compression test"
        },
        {
            "name": "Repeated pattern",
            "data": b"AAAAAAAAAA" * 100,
            "description": "Highly compressible repeated pattern"
        },
        {
            "name": "Random-like data",
            "data": b"The quick brown fox jumps over the lazy dog. " * 20,
            "description": "Mixed content with some repetition"
        },
        {
            "name": "Empty data",
            "data": b"",
            "description": "Edge case: empty input"
        },
        {
            "name": "Single byte",
            "data": b"A",
            "description": "Edge case: single character"
        }
    ]
    
    # Test each case
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"Original size: {len(test_case['data'])} bytes")
        
        try:
            compressed_data = snappy.compress(test_case['data'])
            original_data = test_case['data']
            print("   You'll need to compress the test data first using Snappy.")
            print("original data is ->",original_data)
            print("compressed_data is ->",compressed_data)
            # print(comp)res
            print("   Skipping actual decompression test for now.\n")
            
            # Here's how you would test if you had compressed data:
            
            # Test validation first
            if snappy.is_valid_compressed(compressed_data):
                print("✓ Compressed data is valid")
                
                # Get expected uncompressed length
                # expected_length = len(original_data)
                
                # Test raw_uncompress
                start_time = time.time()
                uncompressed_data = snappy.raw_uncompress_from_source(compressed_data)
                end_time = time.time()
                
                # Verify results
                if uncompressed_data == original_data:
                    print(f"✓ Decompression successful!")
                    print(f"✓ Data integrity verified")
                    print(f"✓ Decompression time: {(end_time - start_time) * 1000:.2f}ms")
                    print(f"  Compressed size: {len(compressed_data)} bytes")
                    print(f"  Compression ratio: {len(original_data) / len(compressed_data):.2f}x")
                else:
                    print("✗ Decompression failed: data mismatch")
            else:
                print("✗ Compressed data validation failed")
            
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
        
        print("-" * 50)
    
    # Test error handling
    print("\n=== Error Handling Tests ===\n")
    
    try:
        print("Test: Invalid compressed data")
        invalid_data = b"This is not compressed data"
        
        # This should return False
        if not snappy.is_valid_compressed(invalid_data):
            print("✓ Invalid data correctly identified")
        else:
            print("✗ Invalid data incorrectly validated")
            
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
    
    print("-" * 50)

def benchmark_performance():
    """Benchmark the performance of decompression"""
    
    print("\n=== Performance Benchmark ===\n")
    
    # Create test data of various sizes
    test_sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB
    
    for size in test_sizes:
        print(f"Testing {size} bytes...")
        
        # Create test data
        test_data = b"A" * (size // 2) + b"B" * (size // 2)
        
        print(f"  Original size: {len(test_data)} bytes")
        print("  Performance test would require actual compression/decompression")
        print("  Skipping for now...\n")


def main():
    """Main test function"""
    
    print("Snappy WASM RawUncompress Test Suite")
    print("====================================\n")
    print("Usage: python main.py [basic|benchmark|interactive]")
    print("\nRunning basic tests by default...\n")
    test_raw_uncompress()

if __name__ == "__main__":
    main()