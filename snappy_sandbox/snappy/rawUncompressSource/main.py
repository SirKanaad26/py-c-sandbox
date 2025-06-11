import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/snappywasm')
# from snappywasm.snappy_sandbox import SnappyWasm
from snappywasm.snappy_sandbox_framework import SnappyWasm
import time

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


def main():
    """Main test function"""
    
    test_raw_uncompress()

if __name__ == "__main__":
    main()