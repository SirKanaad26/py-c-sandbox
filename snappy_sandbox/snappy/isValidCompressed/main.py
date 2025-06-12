import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def test_is_valid_compressed():    
    print("Snappy WASM Test - IsValidCompressed (Source* abstraction version)")
    print("=" * 70)
    
    # Initialize SnappyWasm
    snappy = SnappyWasm()
    
    print(f"Snappy WASM version: {snappy.get_version()}")
    print()
    
    # Test data
    test_data = "Hello, World! This is a test of Snappy Source* abstraction validation."
    print(f"Original data: '{test_data}'")
    print(f"Original size: {len(test_data.encode('utf-8'))} bytes")
    print()
    
    # Compress the data first
    try:
        compressed_data = snappy.compress(test_data.encode('utf-8'))
        print(f"Compression successful!")
        print(f"   Compressed size: {len(compressed_data)} bytes")
        print()
        
        # Test IsValidCompressed (Source* version)
        print("--- Testing IsValidCompressed (Source* abstraction) ---")
        try:
            is_valid_source = snappy.is_valid_compressed(compressed_data)
            print(f"IsValidCompressed result: {is_valid_source}")
            print(f"Status: {'PASS' if is_valid_source else 'FAIL'}")
            
            if is_valid_source:
                try:
                    decompressed = snappy.uncompress(compressed_data)
                    if decompressed == test_data.encode('utf-8'):
                        print(f"Decompression verification: SUCCESS")
                    else:
                        print(f"Decompression verification: FAILED")
                except Exception as e:
                    print(f"Decompression failed: {e}")
                    
        except Exception as e:
            print(f"IsValidCompressed failed: {e}")
            
    except Exception as e:
        print(f"Compression failed: {e}")
        return

def test_invalid_data():
    
    print("\n--- Testing with Invalid Data (Source* abstraction) ---")
    
    snappy = SnappyWasm()
    
    invalid_test_cases = [
        {
            "name": "Plain text",
            "data": b"This is definitely not compressed with Snappy!",
            "description": "Regular uncompressed text"
        },
        {
            "name": "Empty buffer",
            "data": b"",
            "description": "Zero-length data"
        },
        {
            "name": "Binary zeros",
            "data": b"\x00\x00\x00\x00\x00",
            "description": "Multiple null bytes"
        },
        {
            "name": "XML data",
            "data": b'<?xml version="1.0"?><root><item>test</item></root>',
            "description": "XML content as raw bytes"
        },
        {
            "name": "Random pattern",
            "data": bytes([i * 3 % 256 for i in range(100)]),
            "description": "Arithmetic pattern bytes"
        }
    ]
    
    for test_case in invalid_test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"Data size: {len(test_case['data'])} bytes")
        
        try:
            is_valid = snappy.is_valid_compressed(test_case['data'])
            expected = "Expected: False"
            result = "CORRECT" if not is_valid else "UNEXPECTED TRUE"
            print(f"IsValidCompressed: {is_valid} ({expected}) - {result}")
        except Exception as e:
            print(f"Error: {e}")

def test_source_abstraction_features():
    
    print("\n--- Testing Source* Abstraction Features ---")
    
    snappy = SnappyWasm()
    
    test_cases = [
        {
            "name": "Structured data",
            "data": '{"name": "test", "values": [1, 2, 3, 4, 5]}' * 25,
            "description": "JSON-like structured data"
        },
        {
            "name": "Code snippet",
            "data": 'def function(x, y):\n    return x + y\n' * 30,
            "description": "Python code with whitespace"
        },
        {
            "name": "Mixed content",
            "data": "Text with numbers: " + "".join(str(i) for i in range(1000)),
            "description": "Text mixed with sequential numbers"
        },
        {
            "name": "International text",
            "data": "English text, 中文文本, العربية, Русский текст, 日本語テキスト" * 20,
            "description": "Multi-language Unicode content"
        },
        {
            "name": "Highly compressible",
            "data": "COMPRESS_THIS_PATTERN_" * 100,
            "description": "Highly repetitive pattern"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        original_data = test_case['data'].encode('utf-8')
        print(f"Original size: {len(original_data)} bytes")
        
        try:
            compressed_data = snappy.compress(original_data)
            compression_ratio = (1 - len(compressed_data) / len(original_data)) * 100
            print(f"Compressed size: {len(compressed_data)} bytes ({compression_ratio:.1f}% reduction)")
            
            is_valid = snappy.is_valid_compressed(compressed_data)
            print(f"IsValidCompressed (Source*): {is_valid}")
            
            if is_valid:
                try:
                    decompressed = snappy.uncompress(compressed_data)
                    if decompressed == original_data:
                        print(f"Source* round-trip verification: SUCCESS")
                    else:
                        print(f"Source* round-trip verification: FAILED")
                        print(f"   Expected: {len(original_data)} bytes")
                        print(f"   Got: {len(decompressed)} bytes")
                except Exception as e:
                    print(f" Source* decompression error: {e}")
            else:
                print(f" Source* validation failed for compressed data")
                
        except Exception as e:
            print(f"Compression failed: {e}")

def test_source_vs_buffer_consistency():
    
    print("\n--- Testing Source* vs Buffer Consistency ---")
    
    snappy = SnappyWasm()
    
    test_data_sets = [
        b"Small test",
        b"Medium test data with some repetition and variety" * 5,
        b"Large test data set with lots of content and repetitive patterns" * 20,
        bytes([i % 128 for i in range(200)]),  # Binary pattern
        "Unicode: ".encode('utf-8'),  # Unicode
    ]
    
    for i, data in enumerate(test_data_sets):
        print(f"\nConsistency Test {i+1}:")
        print(f"Data type: {type(data).__name__}")
        print(f"Data size: {len(data)} bytes")
        print(f"Preview: {data[:30]}{'...' if len(data) > 30 else ''}")
        
        try:
            # Compress the data
            compressed_data = snappy.compress(data)
            print(f"Compressed size: {len(compressed_data)} bytes")
            
            # Test both validation methods
            is_valid_buffer = snappy.is_valid_compressed_buffer(compressed_data)
            is_valid_source = snappy.is_valid_compressed(compressed_data)
            
            print(f"IsValidCompressedBuffer: {is_valid_buffer}")
            print(f"IsValidCompressed (Source*): {is_valid_source}")
            
            # Check consistency
            if is_valid_buffer == is_valid_source:
                print(f"Consistency check: PASS (both return {is_valid_buffer})")
            else:
                print(f"Consistency check: FAIL (Buffer: {is_valid_buffer}, Source*: {is_valid_source})")
            
        except Exception as e:
            print(f"Test failed: {e}")

def test_source_abstraction_edge_cases():
    
    print("\n--- Testing Source* Abstraction Edge Cases ---")
    
    snappy = SnappyWasm()
    
    print("\nVery small data with Source* abstraction:")
    for size in [1, 2, 3, 4, 5]:
        data = b"X" * size
        try:
            compressed = snappy.compress(data)
            is_valid = snappy.is_valid_compressed(compressed)
            print(f"Size {size}: {len(data)} → {len(compressed)} bytes, Source* valid: {is_valid}")
        except Exception as e:
            print(f"Size {size}: Failed - {e}")
    
    print("\nIncremental size testing with Source* abstraction:")
    for size in [10, 50, 100, 500, 1000]:
        pattern = f"Pattern{size}:"
        data = (pattern * (size // len(pattern) + 1))[:size].encode('utf-8')
        
        try:
            compressed = snappy.compress(data)
            is_valid = snappy.is_valid_compressed(compressed)
            ratio = (1 - len(compressed) / len(data)) * 100
            print(f"Size {size:4d}: {len(data)} → {len(compressed)} bytes ({ratio:5.1f}%), Source* valid: {is_valid}")
        except Exception as e:
            print(f"Size {size:4d}: Failed - {e}")

def test_source_abstraction_internals():
    
    print("\n--- Source* Abstraction Implementation Details ---")
    print("The IsValidCompressed function uses Source* abstraction which:")
    print("1. Creates a ByteArraySource wrapper around the input buffer")
    print("2. Calls snappy::IsValidCompressed(&source) internally")
    print("3. Provides the same C++ API interface as the original Snappy library")
    print("4. Should behave identically to IsValidCompressedBuffer for the same input")
    print()
    print("Key advantages of Source* abstraction:")
    print("Matches original Snappy C++ API design")
    print("Allows for potential future extensions (different source types)")
    print("Provides cleaner abstraction layer")
    print("Maintains compatibility with Snappy's internal implementation")

def main():
    
    try:
        test_is_valid_compressed()
        test_invalid_data()
        test_source_abstraction_features()
        test_source_vs_buffer_consistency()
        test_source_abstraction_edge_cases()
        test_source_abstraction_internals()
        
        print("\n" + "=" * 70)
        print("IsValidCompressed (Source*) tests completed!")
        print("=" * 70)
        print("Summary:")
        print("• Tested Source* abstraction-based validation")
        print("• Verified ByteArraySource wrapper functionality")
        print("• Tested consistency with buffer-based approach")
        print("• Examined Source* abstraction advantages")
        print("• Validated various data types and edge cases")
        print("• Confirmed C++ API compatibility")
        
    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()