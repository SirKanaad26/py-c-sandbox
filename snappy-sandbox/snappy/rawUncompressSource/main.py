#!/usr/bin/env python3
"""
Test script for Snappy WASM RawUncompress functionality.
This script tests the raw_uncompress method from core.py.
"""

import sys
import time
# from core import SnappyWASM
from snappywasm.core import SnappyWasm

def test_raw_uncompress():
    """Test the RawUncompress functionality"""
    
    # Initialize the WASM module
    snappy = SnappyWasm()
    
    # TODO: Initialize your WASM module here
    # This would typically involve loading the WASM file and setting up memory/exports
    # snappy.load_wasm("path/to/your/snappy.wasm")
    
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
            # First, you would need compressed data to test decompression
            # For this test, we'll assume you have a way to compress data first
            # compressed_data = snappy.compress(test_case['data'])  # You'd need this function

            # data = b"hello world " * 10
            compressed_data = snappy.compress(test_case['data'])
            # For demonstration, let's create mock compressed data
            # In reality, you'd get this from actual Snappy compression
            original_data = test_case['data']
            
            print("⚠️  Note: This test requires actual compressed data.")
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
            
        # This should raise an exception when using safe method
        # try:
        #     snappy.raw_uncompress_safe(invalid_data)
        #     print("✗ Safe decompression should have failed")
        # except ValueError as e:
        #     print(f"✓ Safe decompression correctly rejected invalid data: {e}")
            
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

# def interactive_test():
#     """Interactive test mode"""
    
#     print("\n=== Interactive Test Mode ===\n")
    
#     snappy = SnappyWASM()
    
#     while True:
#         print("\nOptions:")
#         print("1. Test with custom text")
#         print("2. Load compressed file")
#         print("3. Exit")
        
#         choice = input("Enter your choice (1-3): ").strip()
        
#         if choice == "1":
#             text = input("Enter text to test: ")
#             data = text.encode('utf-8')
#             print(f"Text length: {len(data)} bytes")
#             print("Note: You would need to compress this first before testing decompression")
            
#         elif choice == "2":
#             filename = input("Enter compressed file path: ")
#             try:
#                 with open(filename, 'rb') as f:
#                     compressed_data = f.read()
#                 print(f"Loaded {len(compressed_data)} bytes from {filename}")
                
#                 # Test validation
#                 if snappy.is_valid_compressed(compressed_data):
#                     print("✓ File contains valid Snappy compressed data")
                    
#                     # You would need to know or detect the uncompressed length
#                     max_length = int(input("Enter maximum expected uncompressed length: "))
                    
#                     try:
#                         result = snappy.raw_uncompress_safe(compressed_data, max_length)
#                         print(f"✓ Successfully decompressed to {len(result)} bytes")
                        
#                         # Optionally save result
#                         save = input("Save decompressed data to file? (y/n): ").lower()
#                         if save == 'y':
#                             output_file = input("Enter output filename: ")
#                             with open(output_file, 'wb') as f:
#                                 f.write(result)
#                             print(f"Saved to {output_file}")
                            
#                     except Exception as e:
#                         print(f"✗ Decompression failed: {e}")
#                 else:
#                     print("✗ File does not contain valid Snappy compressed data")
                    
#             except FileNotFoundError:
#                 print(f"✗ File not found: {filename}")
#             except Exception as e:
#                 print(f"✗ Error reading file: {e}")
                
#         elif choice == "3":
#             break
#         else:
#             print("Invalid choice. Please try again.")

def main():
    """Main test function"""
    
    print("Snappy WASM RawUncompress Test Suite")
    print("====================================\n")
    
    # if len(sys.argv) > 1:
    #     mode = sys.argv[1].lower()
        
    #     if mode == "basic":
    #         test_raw_uncompress()
    #     elif mode == "benchmark":
    #         benchmark_performance()
    #     elif mode == "interactive":
    #         interactive_test()
    #     else:
    #         print(f"Unknown mode: {mode}")
    #         print("Available modes: basic, benchmark, interactive")
    # else:
    print("Usage: python main.py [basic|benchmark|interactive]")
    print("\nRunning basic tests by default...\n")
    test_raw_uncompress()

if __name__ == "__main__":
    main()