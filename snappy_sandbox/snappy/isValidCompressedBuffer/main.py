import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm


class SnappyIsValidCompressedBufferTester:
    def __init__(self):
        self.snappy = SnappyWasm()
    
    def create_test_data(self):
        return "Hello, World! This is a test of Snappy compression validation."
    
    def test_valid_compressed_buffer(self, test_data):
        print("=== Valid Compressed Buffer Test ===")
        print(f"Original data: '{test_data}'")
        print(f"Original size: {len(test_data.encode('utf-8'))} bytes")
        
        try:
            compressed_data = self.snappy.compress(test_data.encode('utf-8'))
            print(f"Compressed size: {len(compressed_data)} bytes")
            
            is_valid_buffer = self.snappy.is_valid_compressed_buffer(compressed_data)
            print(f"IsValidCompressedBuffer result: {is_valid_buffer}")
            print(f"Status: {'PASS' if is_valid_buffer else 'FAIL'}")
            
            if is_valid_buffer:
                try:
                    decompressed = self.snappy.uncompress(compressed_data)
                    if decompressed == test_data.encode('utf-8'):
                        print(f"Decompression verification: SUCCESS")
                    else:
                        print(f"Decompression verification: FAILED")
                except Exception as e:
                    print(f"Decompression failed: {e}")
                    
        except Exception as e:
            print(f"Compression failed: {e}")
    
    def create_invalid_test_cases(self):
        return [
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
    
    def test_invalid_data(self):
        print("\n=== Invalid Data Test ===")
        
        invalid_test_cases = self.create_invalid_test_cases()
        
        for test_case in invalid_test_cases:
            print(f"\nTest: {test_case['name']}")
            print(f"Description: {test_case['description']}")
            print(f"Data size: {len(test_case['data'])} bytes")
            
            try:
                is_valid = self.snappy.is_valid_compressed_buffer(test_case['data'])
                result = "CORRECT" if not is_valid else "UNEXPECTED TRUE"
                print(f"IsValidCompressedBuffer: {is_valid} (Expected: False) - {result}")
            except Exception as e:
                print(f"Error: {e}")
    
    def create_multiple_data_test_cases(self):
        return [
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
                "data": "Hello 世界 Привет мир",
                "description": "Unicode characters"
            }
        ]
    
    def test_multiple_data_types(self):
        print("\n=== Multiple Data Types Test ===")
        
        test_cases = self.create_multiple_data_test_cases()
        
        for test_case in test_cases:
            print(f"\nTest: {test_case['name']}")
            print(f"Description: {test_case['description']}")
            original_data = test_case['data'].encode('utf-8')
            print(f"Original size: {len(original_data)} bytes")
            
            try:
                compressed_data = self.snappy.compress(original_data)
                compression_ratio = (1 - len(compressed_data) / len(original_data)) * 100
                print(f"Compressed size: {len(compressed_data)} bytes ({compression_ratio:.1f}% reduction)")
                
                is_valid = self.snappy.is_valid_compressed_buffer(compressed_data)
                print(f"IsValidCompressedBuffer: {is_valid}")
                
                if is_valid:
                    try:
                        decompressed = self.snappy.uncompress(compressed_data)
                        if decompressed == original_data:
                            print(f"Round-trip verification: SUCCESS")
                        else:
                            print(f"Round-trip verification: FAILED")
                    except Exception as e:
                        print(f"Decompression error: {e}")
                else:
                    print(f"Validation failed for compressed data")
                    
            except Exception as e:
                print(f"Compression failed: {e}")
    
    def test_edge_cases(self):
        print("\n=== Edge Cases Test ===")
        
        print("\nMinimum size data:")
        for size in [1, 2, 3, 5, 10]:
            data = b"A" * size
            try:
                compressed = self.snappy.compress(data)
                is_valid = self.snappy.is_valid_compressed_buffer(compressed)
                print(f"Size {size:2d}: {len(data)} → {len(compressed)} bytes, valid: {is_valid}")
            except Exception as e:
                print(f"Size {size:2d}: Failed - {e}")
        
        print("\nLarger data sizes:")
        for size in [100, 500, 1000, 2000]:
            data = f"Test data of size {size}: " + "x" * (size - 20)
            data_bytes = data.encode('utf-8')
            try:
                compressed = self.snappy.compress(data_bytes)
                is_valid = self.snappy.is_valid_compressed_buffer(compressed)
                ratio = (1 - len(compressed) / len(data_bytes)) * 100
                print(f"Size {size:4d}: {len(data_bytes)} → {len(compressed)} bytes ({ratio:.1f}%), valid: {is_valid}")
            except Exception as e:
                print(f"Size {size:4d}: Failed - {e}")
    
    def create_malformed_test_cases(self):
        return [
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
                "data": b"\x0C",
                "description": "Single byte that could be part of length encoding"
            }
        ]
    
    def test_malformed_data(self):
        print("\n=== Malformed Data Test ===")
        
        malformed_cases = self.create_malformed_test_cases()
        
        for test_case in malformed_cases:
            print(f"\nTest: {test_case['name']}")
            print(f"Description: {test_case['description']}")
            print(f"Data: {test_case['data'][:20]}{'...' if len(test_case['data']) > 20 else ''}")
            print(f"Size: {len(test_case['data'])} bytes")
            
            try:
                is_valid = self.snappy.is_valid_compressed_buffer(test_case['data'])
                print(f"IsValidCompressedBuffer: {is_valid} (Expected: False)")
                if is_valid:
                    print(f"Unexpected: Data validated as compressed!")
                else:
                    print(f"Correctly identified as invalid")
            except Exception as e:
                print(f"Error during validation: {e}")
    
    def run_all_tests(self):
        test_data = self.create_test_data()
        self.test_valid_compressed_buffer(test_data)
        self.test_invalid_data()
        self.test_multiple_data_types()
        self.test_edge_cases()
        self.test_malformed_data()


def main():
    tester = SnappyIsValidCompressedBufferTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()