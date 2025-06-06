# main.py
# Example usage of the Snappy Cython wrapper

import snappy_wrapper
import time

def main():
    # Test data
    test_data = b"Hello, World! This is a test string for Snappy compression."
    print(f"Original data: {test_data}")
    print(f"Original size: {len(test_data)} bytes")
    
    # Calculate maximum compressed length
    max_compressed_size = snappy_wrapper.max_compressed_length(len(test_data))
    print(f"Maximum compressed size: {max_compressed_size} bytes")
    
    # Test compression options
    print(f"\nCompression level info:")
    print(f"Min level: {snappy_wrapper.PyCompressionOptions.min_level()}")
    print(f"Max level: {snappy_wrapper.PyCompressionOptions.max_level()}")
    print(f"Default level: {snappy_wrapper.PyCompressionOptions.default_level()}")
    
    try:
        # Test string-based compression with default options
        print("\n--- Testing string-based compression (default) ---")
        compressed_data = snappy_wrapper.compress_data(test_data)
        print(f"Actual compressed size: {len(compressed_data)} bytes")
        print(f"Compression ratio: {len(test_data) / len(compressed_data):.2f}")
        
        # Check if valid compressed buffer
        is_valid = snappy_wrapper.is_valid_compressed_buffer(compressed_data)
        print(f"Is valid compressed buffer: {is_valid}")
        
        # Get uncompressed length from compressed data
        uncompressed_length = snappy_wrapper.get_uncompressed_length(compressed_data)
        print(f"Uncompressed length from compressed data: {uncompressed_length} bytes")
        
        # Decompress the data
        decompressed_data = snappy_wrapper.uncompress_data(compressed_data)
        print(f"Decompressed data: {decompressed_data}")
        print(f"Decompressed size: {len(decompressed_data)} bytes")
        
        # Verify the data integrity
        if test_data == decompressed_data:
            print("✓ String-based compression/decompression successful!")
        else:
            print("✗ String-based compression/decompression failed!")
        
        # Test with compression level 2
        print("\n--- Testing compression with level 2 ---")
        opt2 = snappy_wrapper.PyCompressionOptions(level=2)
        compressed_l2 = snappy_wrapper.compress_data(test_data, opt2)
        print(f"Level 2 compressed size: {len(compressed_l2)} bytes")
        print(f"Level 2 compression ratio: {len(test_data) / len(compressed_l2):.2f}")
        
        decompressed_l2 = snappy_wrapper.uncompress_data(compressed_l2)
        if test_data == decompressed_l2:
            print("✓ Level 2 compression/decompression successful!")
        
        # Test raw compression
        print("\n--- Testing raw compression ---")
        raw_compressed = snappy_wrapper.compress_raw(test_data)
        print(f"Raw compressed size: {len(raw_compressed)} bytes")
        
        raw_decompressed = snappy_wrapper.uncompress_raw(raw_compressed)
        if test_data == raw_decompressed:
            print("✓ Raw compression/decompression successful!")
        else:
            print("✗ Raw compression/decompression failed!")
        
        # Test raw compression with level 2
        print("\n--- Testing raw compression with level 2 ---")
        raw_compressed_l2 = snappy_wrapper.compress_raw(test_data, opt2)
        print(f"Raw level 2 compressed size: {len(raw_compressed_l2)} bytes")
        
        raw_decompressed_l2 = snappy_wrapper.uncompress_raw(raw_compressed_l2)
        if test_data == raw_decompressed_l2:
            print("✓ Raw level 2 compression/decompression successful!")
        
        # Test with larger data
        print("\n--- Testing with larger data ---")
        large_data = b"hello world " * 1000
        print(f"Large data size: {len(large_data)} bytes")
        
        compressed_large = snappy_wrapper.compress_data(large_data)
        print(f"Compressed size (level 1): {len(compressed_large)} bytes")
        print(f"Compression ratio: {len(large_data) / len(compressed_large):.2f}")
        
        compressed_large_l2 = snappy_wrapper.compress_data(large_data, opt2)
        print(f"Compressed size (level 2): {len(compressed_large_l2)} bytes")
        print(f"Compression ratio: {len(large_data) / len(compressed_large_l2):.2f}")
        
        decompressed_large = snappy_wrapper.uncompress_data(compressed_large)
        if large_data == decompressed_large:
            print("✓ Large data compression/decompression successful!")
    
    except RuntimeError as e:
        print(f"Error: {e}")

def test_various_sizes():
    """Test MaxCompressedLength with various input sizes"""
    print("\n--- Testing MaxCompressedLength with various sizes ---")
    
    test_sizes = [0, 1, 10, 100, 1000, 10000, 100000, 1000000]
    
    for size in test_sizes:
        max_size = snappy_wrapper.max_compressed_length(size)
        overhead = max_size - size if size > 0 else max_size
        overhead_percent = (overhead / size * 100) if size > 0 else 0
        
        print(f"Input: {size:8} bytes -> Max compressed: {max_size:8} bytes "
              f"(overhead: {overhead:6} bytes, {overhead_percent:5.1f}%)")

def benchmark_compression():
    """Benchmark compression performance"""
    print("\n--- Compression Performance Benchmark ---")
    
    # Generate test data of various sizes
    test_sizes = [(1024, "1KB"), (10*1024, "10KB"), (100*1024, "100KB"), (1024*1024, "1MB")]
    
    for size, label in test_sizes:
        # Generate somewhat compressible data
        data = (b"The quick brown fox jumps over the lazy dog. " * (size // 45))[:size]
        
        # Measure compression time
        start_time = time.time()
        compressed = snappy_wrapper.compress_data(data)
        compress_time = time.time() - start_time
        
        # Measure decompression time
        start_time = time.time()
        decompressed = snappy_wrapper.uncompress_data(compressed)
        decompress_time = time.time() - start_time
        
        # Calculate metrics
        compression_ratio = len(data) / len(compressed)
        compress_speed = size / compress_time / (1024*1024)  # MB/s
        decompress_speed = size / decompress_time / (1024*1024)  # MB/s
        
        print(f"\n{label} ({size} bytes):")
        print(f"  Compression ratio: {compression_ratio:.2f}x")
        print(f"  Compression speed: {compress_speed:.1f} MB/s")
        print(f"  Decompression speed: {decompress_speed:.1f} MB/s")
        
        # Verify data integrity
        assert data == decompressed, f"Data integrity check failed for {label}"

if __name__ == "__main__":
    main()
    test_various_sizes()
    benchmark_compression()