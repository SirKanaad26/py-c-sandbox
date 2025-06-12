import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def test_uncompress():
    
    print("Testing Snappy Uncompress Function")
    print("=" * 50)
    
    snappy = SnappyWasm()
    
    original_data = b"Hello, World! This is a test of Snappy compression and decompression."
    print(f"Original: {original_data.decode()}")
    print(f"Size: {len(original_data)} bytes")
    
    try:
        compressed = snappy.compress(original_data)
        print(f"Compressed size: {len(compressed)} bytes")
        
        uncompressed = snappy.uncompress(compressed)
        print(f"Uncompressed size: {len(uncompressed)} bytes")
        
        if uncompressed == original_data:
            print("Test PASSED - Data integrity maintained")
            print(f"Uncompressed: {uncompressed.decode()}")
            return True
        else:
            print("Test FAILED - Data mismatch")
            return False
            
    except Exception as e:
        print(f"Test FAILED: {e}")
        return False

def test_multiple_sizes():
    
    print("\nTesting Multiple Data Sizes")
    print("-" * 30)
    
    snappy = SnappyWasm()
    
    test_cases = [
        b"A",  
        b"Hello!",  
        b"The quick brown fox jumps over the lazy dog.",
        b"PATTERN" * 100, 
        bytes(range(256)),
    ]
    
    passed = 0
    for i, data in enumerate(test_cases):
        try:
            compressed = snappy.compress(data)
            uncompressed = snappy.uncompress(compressed)
            
            if uncompressed == data:
                print(f"Test {i+1}: {len(data)} bytes - PASSED")
                passed += 1
            else:
                print(f"Test {i+1}: {len(data)} bytes - FAILED")
                
        except Exception as e:
            print(f"Test {i+1}: {len(data)} bytes - ERROR: {e}")
    
    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_error_handling():
    
    print("\nTesting Error Handling")
    print("-" * 25)
    
    snappy = SnappyWasm()
    
    invalid_cases = [
        b"",  
        b"invalid compressed data", 
        b"\x00\x01\x02\x03", 
    ]
    
    for i, invalid_data in enumerate(invalid_cases):
        try:
            snappy.uncompress(invalid_data)
            print(f"Test {i+1}: Unexpected success with invalid data")
        except Exception as e:
            print(f"Test {i+1}: Correctly failed - {type(e).__name__}")

if __name__ == "__main__":
    success1 = test_uncompress()
    success2 = test_multiple_sizes()
    test_error_handling()
    
    if success1 and success2:
        print("\nAll critical tests passed!")
        sys.exit(0)
    else:
        print("\n Some tests failed")
        sys.exit(1)