#!/usr/bin/env python3
"""
Test file for IsValidCompressedBuffer function using SnappyWasm class
Tests the char* buffer version of the validation function
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/snappywasm')
# from snappywasm.snappy_sandbox import SnappyWasm
from snappywasm.snappy_sandbox_framework import SnappyWasm

def test_is_valid_compressed_buffer():
    """Test the is_valid_compressed_buffer method"""
    
    
    # Initialize SnappyWasm
    snappy = SnappyWasm()
    
    
    # Test data
    test_data = "Hello, World! This is a test of Snappy compression validation."
    print(f"Original data: '{test_data}'")
    print(f"Original size: {len(test_data.encode('utf-8'))} bytes")
    print()
    
    # Compress the data first
    try:
        compressed_data = snappy.compress(test_data.encode('utf-8'))
        print(f"✅ Compression successful!")
        print(f"   Compressed size: {len(compressed_data)} bytes")
        print()
        
        # Test IsValidCompressedBuffer
        print("--- Testing IsValidCompressedBuffer ---")
        try:
            is_valid_buffer = snappy.is_valid_compressed_buffer(compressed_data)
            print(f"IsValidCompressedBuffer result: {is_valid_buffer}")
            print(f"Status: {'✅ PASS' if is_valid_buffer else '❌ FAIL'}")
            
            # Verify with decompression if valid
            if is_valid_buffer:
                try:
                    decompressed = snappy.uncompress(compressed_data)
                    if decompressed == test_data.encode('utf-8'):
                        print(f"✅ Decompression verification: SUCCESS")
                    else:
                        print(f"❌ Decompression verification: FAILED")
                except Exception as e:
                    print(f"❌ Decompression failed: {e}")
                    
        except Exception as e:
            print(f"❌ IsValidCompressedBuffer failed: {e}")
            
    except Exception as e:
        print(f"❌ Compression failed: {e}")
        return

def test_invalid_data():
    """Test validation function with invalid data"""
    
    print("\n--- Testing with Invalid Data ---")
    
    snappy = SnappyWasm()
    
    invalid_test_cases = [
        {
            "name": "Random text",
            "data": b"This is not compressed data at all!",
            "description": "Regular text as bytes"
        },
        {
            "name": "Empty data",
            "data": b"",
            "description": "Empty byte string"
        },
        {
            "name": "Single byte",
            "data": b"\x00",
            "description": "Single null byte"
        },
        {
            "name": "JSON data",
            "data": b'{"invalid": "compressed", "data": true}',
            "description": "JSON as raw bytes"
        },
        {
            "name": "Binary sequence",
            "data": bytes(range(50)),
            "description": "Sequential byte values 0-49"
        }
    ]
    
    for test_case in invalid_test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"Data size: {len(test_case['data'])} bytes")
        
        try:
            is_valid = snappy.is_valid_compressed_buffer(test_case['data'])
            expected = "Expected: False"
            result = "✅ CORRECT" if not is_valid else "⚠️ UNEXPECTED TRUE"
            print(f"IsValidCompressedBuffer: {is_valid} ({expected}) - {result}")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_multiple_data_types():
    """Test validation with different types of compressed data"""
    
    print("\n--- Testing Multiple Data Types ---")
    
    snappy = SnappyWasm()
    
    test_cases = [
        {
            "name": "Short text",
            "data": "Hi!",
            "description": "Very short text"
        },
        {
            "name": "Repetitive pattern",
            "data": "ABCD" * 50,
            "description": "Repeating 4-character pattern"
        },
        {
            "name": "Lorem ipsum",
            "data": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,
            "description": "Standard lorem ipsum text"
        },
        {
            "name": "Numbers and symbols",
            "data": "1234567890!@#$%^&*()_+-=[]{}|;:,.<>?" * 20,
            "description": "Mixed numbers and symbols"
        },
        {
            "name": "Unicode text",
            "data": "Hello 世界 🌍 Привет мир 🚀",
            "description": "Unicode characters and emojis"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        original_data = test_case['data'].encode('utf-8')
        print(f"Original size: {len(original_data)} bytes")
        
        try:
            # Compress the data
            compressed_data = snappy.compress(original_data)
            compression_ratio = (1 - len(compressed_data) / len(original_data)) * 100
            print(f"Compressed size: {len(compressed_data)} bytes ({compression_ratio:.1f}% reduction)")
            
            # Test validation
            is_valid = snappy.is_valid_compressed_buffer(compressed_data)
            print(f"IsValidCompressedBuffer: {is_valid}")
            
            if is_valid:
                # Verify decompression
                try:
                    decompressed = snappy.uncompress(compressed_data)
                    if decompressed == original_data:
                        print(f"✅ Round-trip verification: SUCCESS")
                    else:
                        print(f"❌ Round-trip verification: FAILED")
                except Exception as e:
                    print(f"❌ Decompression error: {e}")
            else:
                print(f"⚠️ Validation failed for compressed data")
                
        except Exception as e:
            print(f"❌ Compression failed: {e}")

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    
    print("\n--- Testing Edge Cases ---")
    
    snappy = SnappyWasm()
    
    # Test minimum size data
    print("\nMinimum size data:")
    for size in [1, 2, 3, 5, 10]:
        data = b"A" * size
        try:
            compressed = snappy.compress(data)
            is_valid = snappy.is_valid_compressed_buffer(compressed)
            print(f"Size {size:2d}: {len(data)} → {len(compressed)} bytes, valid: {is_valid}")
        except Exception as e:
            print(f"Size {size:2d}: Failed - {e}")
    
    # Test larger data sizes
    print("\nLarger data sizes:")
    for size in [100, 500, 1000, 2000]:
        data = f"Test data of size {size}: " + "x" * (size - 20)
        data_bytes = data.encode('utf-8')
        try:
            compressed = snappy.compress(data_bytes)
            is_valid = snappy.is_valid_compressed_buffer(compressed)
            ratio = (1 - len(compressed) / len(data_bytes)) * 100
            print(f"Size {size:4d}: {len(data_bytes)} → {len(compressed)} bytes ({ratio:.1f}%), valid: {is_valid}")
        except Exception as e:
            print(f"Size {size:4d}: Failed - {e}")

def test_malformed_data():
    """Test with potentially malformed compressed data"""
    
    print("\n--- Testing Malformed Data ---")
    
    snappy = SnappyWasm()
    
    # Test data that might look like compressed data but isn't
    malformed_cases = [
        {
            "name": "Short random bytes",
            "data": b"\x01\x02\x03\x04\x05",
            "description": "Short sequence that might be mistaken for header"
        },
        {
            "name": "Long random data",
            "data": bytes([i % 256 for i in range(100)]),
            "description": "Longer random byte sequence"
        },
        {
            "name": "Null bytes",
            "data": b"\x00" * 50,
            "description": "All null bytes"
        },
        {
            "name": "High values",
            "data": b"\xFF" * 20,
            "description": "All 0xFF bytes"
        },
        {
            "name": "Truncated header",
            "data": b"\x0C",  # This might look like a length but is incomplete
            "description": "Single byte that could be part of length encoding"
        }
    ]
    
    for test_case in malformed_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"Data: {test_case['data'][:20]}{'...' if len(test_case['data']) > 20 else ''}")
        print(f"Size: {len(test_case['data'])} bytes")
        
        try:
            is_valid = snappy.is_valid_compressed_buffer(test_case['data'])
            print(f"IsValidCompressedBuffer: {is_valid} (Expected: False)")
            if is_valid:
                print(f"⚠️ Unexpected: Data validated as compressed!")
            else:
                print(f"✅ Correctly identified as invalid")
        except Exception as e:
            print(f"❌ Error during validation: {e}")

def main():
    """Main test function"""
    
    try:
        test_is_valid_compressed_buffer()
        # test_invalid_data()
        # test_multiple_data_types()
        # test_edge_cases()
        # test_malformed_data()
        
        # print("\n" + "=" * 70)
        # print("✅ IsValidCompressedBuffer tests completed!")
        # print("=" * 70)
        # print("Summary:")
        # print("• Tested char* buffer-based validation")
        # print("• Verified with valid compressed data")
        # print("• Tested rejection of invalid data")
        # print("• Checked various data types and sizes")
        # print("• Examined edge cases and malformed data")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    main()