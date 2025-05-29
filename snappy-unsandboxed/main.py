# main.py
# Example usage of the Snappy Cython wrapper

import snappy_wrapper

def main():
    # Test data
    test_data = b"Hello, World! This is a test string for Snappy compression."
    print(f"Original data: {test_data}")
    print(f"Original size: {len(test_data)} bytes")
    
    # Calculate maximum compressed length
    max_compressed_size = snappy_wrapper.max_compressed_length(len(test_data))
    print(f"Maximum compressed size: {max_compressed_size} bytes")
    
    try:
        # Compress the data
        compressed_data = snappy_wrapper.compress_data(test_data)
        print(f"Actual compressed size: {len(compressed_data)} bytes")
        print(f"Compression ratio: {len(test_data) / len(compressed_data):.2f}")
        
        # Decompress the data
        decompressed_data = snappy_wrapper.uncompress_data(compressed_data)
        print(f"Decompressed data: {decompressed_data}")
        print(f"Decompressed size: {len(decompressed_data)} bytes")
        
        # Verify the data integrity
        if test_data == decompressed_data:
            print("✓ Data integrity verified - compression/decompression successful!")
        else:
            print("✗ Data integrity check failed!")
        
        data = b"hello world " * 100

        # Use compression level 2 (higher compression)
        opt = snappy_wrapper.PyCompressionOptions(level=2)

        compressed = snappy_wrapper.cython_CompressWithCustomOptions(data, opt)
        print(f"Compressed length: {len(compressed)} with level {opt.get_level()}")
    
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

if __name__ == "__main__":
    main()
    test_various_sizes()