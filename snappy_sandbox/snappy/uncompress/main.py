#!/usr/bin/env python3
"""
Minimal test for the uncompress function using SnappyWasm class
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm

def test_uncompress():
    """Test basic uncompress functionality"""
    
    print("🧪 Testing Snappy Uncompress Function")
    print("=" * 50)
    
    # Initialize SnappyWasm
    snappy = SnappyWasm()
    
    # Test data
    original_data = b"Hello, World! This is a test of Snappy compression and decompression."
    print(f"Original: {original_data.decode()}")
    print(f"Size: {len(original_data)} bytes")
    
    try:
        # Compress first
        compressed = snappy.compress(original_data)
        print(f"Compressed size: {len(compressed)} bytes")
        
        # Test uncompress
        uncompressed = snappy.uncompress(compressed)
        print(f"Uncompressed size: {len(uncompressed)} bytes")
        
        # Verify integrity
        if uncompressed == original_data:
            print("✅ Test PASSED - Data integrity maintained")
            print(f"Uncompressed: {uncompressed.decode()}")
            return True
        else:
            print("❌ Test FAILED - Data mismatch")
            return False
            
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        return False

def test_multiple_sizes():
    """Test uncompress with different data sizes"""
    
    print("\n📏 Testing Multiple Data Sizes")
    print("-" * 30)
    
    snappy = SnappyWasm()
    
    test_cases = [
        b"A",  # Single byte
        b"Hello!",  # Short string
        b"The quick brown fox jumps over the lazy dog.",  # Medium string
        b"PATTERN" * 100,  # Repetitive data
        bytes(range(256)),  # Binary data
    ]
    
    passed = 0
    for i, data in enumerate(test_cases):
        try:
            compressed = snappy.compress(data)
            uncompressed = snappy.uncompress(compressed)
            
            if uncompressed == data:
                print(f"✅ Test {i+1}: {len(data)} bytes - PASSED")
                passed += 1
            else:
                print(f"❌ Test {i+1}: {len(data)} bytes - FAILED")
                
        except Exception as e:
            print(f"❌ Test {i+1}: {len(data)} bytes - ERROR: {e}")
    
    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_error_handling():
    """Test error handling with invalid data"""
    
    print("\n⚠️ Testing Error Handling")
    print("-" * 25)
    
    snappy = SnappyWasm()
    
    invalid_cases = [
        b"",  # Empty data
        b"invalid compressed data",  # Random text
        b"\x00\x01\x02\x03",  # Random bytes
    ]
    
    for i, invalid_data in enumerate(invalid_cases):
        try:
            snappy.uncompress(invalid_data)
            print(f"⚠️ Test {i+1}: Unexpected success with invalid data")
        except Exception as e:
            print(f"✅ Test {i+1}: Correctly failed - {type(e).__name__}")

if __name__ == "__main__":
    success1 = test_uncompress()
    success2 = test_multiple_sizes()
    test_error_handling()
    
    if success1 and success2:
        print("\n🎉 All critical tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)