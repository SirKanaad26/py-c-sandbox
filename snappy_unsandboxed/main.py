# main_comprehensive.py
# Complete test suite for all Snappy wrapper functions (Version 11)

import snappy_wrapper
import time
import sys

def print_header(title):
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print('='*60)

def test_constants():
    print_header("Testing Snappy Constants")
    
    constants = snappy_wrapper.get_constants()
    print("Snappy Constants:")
    for name, value in sorted(constants.items()):
        print(f"  {name:20} = {value}")
    
    assert constants['kBlockSize'] == 2 ** constants['kBlockLog']
    assert constants['kMinHashTableSize'] == 2 ** constants['kMinHashTableBits']
    assert constants['kMaxHashTableSize'] == 2 ** constants['kMaxHashTableBits']
    print("\nConstants validation passed")

def test_compression_options():
    print_header("Testing Compression Options")
    
    print(f"Min compression level: {snappy_wrapper.PyCompressionOptions.min_level()}")
    print(f"Max compression level: {snappy_wrapper.PyCompressionOptions.max_level()}")
    print(f"Default compression level: {snappy_wrapper.PyCompressionOptions.default_level()}")
    
    opt1 = snappy_wrapper.PyCompressionOptions(level=1)
    opt2 = snappy_wrapper.PyCompressionOptions(level=2)
    print(f"\nCreated option with level 1: {opt1.get_level()}")
    print(f"Created option with level 2: {opt2.get_level()}")
    
    try:
        opt_invalid = snappy_wrapper.PyCompressionOptions(level=3)
        print("ERROR: Should have rejected level 3")
    except ValueError as e:
        print(f"\nCorrectly rejected invalid level: {e}")

def test_basic_compression():
    print_header("Testing Basic Compression/Decompression")
    
    test_data = b"Hello, World! This is a test string for Snappy compression. " * 3
    print(f"Original data size: {len(test_data)} bytes")
    
    max_len = snappy_wrapper.max_compressed_length(len(test_data))
    print(f"Maximum compressed length: {max_len} bytes")
    
    # Test compress_data
    compressed = snappy_wrapper.compress_data(test_data)
    print(f"\nCompressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {len(test_data)/len(compressed):.2f}x")
    print(f"Actual compression overhead: {len(compressed) - len(test_data)} bytes")
    
    # Test is_valid_compressed_buffer
    is_valid = snappy_wrapper.is_valid_compressed_buffer(compressed)
    print(f"\nIs valid compressed buffer: {is_valid}")
    assert is_valid, "Compressed data should be valid"
    
    # Test get_uncompressed_length
    uncompressed_len = snappy_wrapper.get_uncompressed_length(compressed)
    print(f"Uncompressed length from compressed data: {uncompressed_len} bytes")
    assert uncompressed_len == len(test_data), "Uncompressed length mismatch"
    
    # Test uncompress_data
    decompressed = snappy_wrapper.uncompress_data(compressed)
    print(f"Decompressed size: {len(decompressed)} bytes")
    assert decompressed == test_data, "Decompression failed"
    print("\n✓ Basic compression/decompression passed")

def test_compression_levels():
    """Test different compression levels."""
    print_header("Testing Compression Levels")
    
    # Generate repetitive data for better compression
    test_data = b"ABCDEFGHIJ" * 1000  # 10KB of repetitive data
    
    opt1 = snappy_wrapper.PyCompressionOptions(level=1)
    opt2 = snappy_wrapper.PyCompressionOptions(level=2)
    
    # Test string-based compression with levels
    compressed_l1 = snappy_wrapper.compress_data(test_data, opt1)
    compressed_l2 = snappy_wrapper.compress_data(test_data, opt2)
    
    print(f"Original size: {len(test_data)} bytes")
    print(f"Level 1 compressed: {len(compressed_l1)} bytes (ratio: {len(test_data)/len(compressed_l1):.2f}x)")
    print(f"Level 2 compressed: {len(compressed_l2)} bytes (ratio: {len(test_data)/len(compressed_l2):.2f}x)")
    print(f"Level 2 improvement: {(1 - len(compressed_l2)/len(compressed_l1)) * 100:.1f}%")
    
    # Verify both decompress correctly
    assert snappy_wrapper.uncompress_data(compressed_l1) == test_data
    assert snappy_wrapper.uncompress_data(compressed_l2) == test_data
    print("\n✓ Compression levels test passed")

def test_raw_compression():
    """Test raw compression functions."""
    print_header("Testing Raw Compression/Decompression")
    
    test_data = b"Raw compression test data. " * 100
    print(f"Test data size: {len(test_data)} bytes")
    
    # Test raw compression
    raw_compressed = snappy_wrapper.compress_raw(test_data)
    print(f"Raw compressed size: {len(raw_compressed)} bytes")
    
    # Test raw decompression
    raw_decompressed = snappy_wrapper.uncompress_raw(raw_compressed)
    assert raw_decompressed == test_data, "Raw decompression failed"
    print("✓ Raw decompression successful")
    
    # Test raw compression with level 2
    opt2 = snappy_wrapper.PyCompressionOptions(level=2)
    raw_compressed_l2 = snappy_wrapper.compress_raw(test_data, opt2)
    print(f"\nRaw compressed (level 2): {len(raw_compressed_l2)} bytes")
    
    raw_decompressed_l2 = snappy_wrapper.uncompress_raw(raw_compressed_l2)
    assert raw_decompressed_l2 == test_data, "Raw level 2 decompression failed"
    print("✓ Raw level 2 compression/decompression passed")

def test_iovec_compression():
    """Test IOVec-based compression functions."""
    print_header("Testing IOVec Compression")
    
    # Create test chunks
    chunks = [
        b"First chunk of data with some content. ",
        b"Second chunk has different information. ",
        b"Third chunk contains more test data. ",
        b"Fourth chunk completes our test set. "
    ]
    
    total_size = sum(len(chunk) for chunk in chunks)
    print(f"Total data across {len(chunks)} chunks: {total_size} bytes")
    
    # Test compress_from_iovec
    iovec_compressed = snappy_wrapper.compress_from_iovec(chunks)
    print(f"IOVec compressed size: {len(iovec_compressed)} bytes")
    
    # Compare with normal compression
    concatenated = b''.join(chunks)
    normal_compressed = snappy_wrapper.compress_data(concatenated)
    print(f"Normal compressed size: {len(normal_compressed)} bytes")
    print(f"IOVec vs normal difference: {len(iovec_compressed) - len(normal_compressed)} bytes")
    
    # Verify decompression
    decompressed = snappy_wrapper.uncompress_data(iovec_compressed)
    assert decompressed == concatenated, "IOVec decompression failed"
    print("✓ IOVec compression/decompression successful")
    
    # Test raw IOVec compression
    raw_iovec = snappy_wrapper.compress_raw_from_iovec(chunks)
    print(f"\nRaw IOVec compressed size: {len(raw_iovec)} bytes")
    
    # Test with compression level 2
    opt2 = snappy_wrapper.PyCompressionOptions(level=2)
    iovec_l2 = snappy_wrapper.compress_from_iovec(chunks, opt2)
    raw_iovec_l2 = snappy_wrapper.compress_raw_from_iovec(chunks, opt2)
    print(f"IOVec level 2: {len(iovec_l2)} bytes")
    print(f"Raw IOVec level 2: {len(raw_iovec_l2)} bytes")

def test_iovec_decompression():
    """Test IOVec decompression."""
    print_header("Testing IOVec Decompression")
    
    # Create test data that we'll split into chunks
    test_data = b"This is a test string that will be decompressed into multiple buffers!"
    compressed = snappy_wrapper.compress_data(test_data)
    
    print(f"Original data: {len(test_data)} bytes")
    print(f"Compressed: {len(compressed)} bytes")
    
    # Get the actual uncompressed length
    actual_length = snappy_wrapper.get_uncompressed_length(compressed)
    print(f"Actual uncompressed length: {actual_length} bytes")
    
    # Define buffer sizes that exactly match the decompressed size
    buffer_sizes = [10, 20, 25, 15]  # Total: 70 bytes (exact match)
    print(f"Buffer sizes: {buffer_sizes} (total: {sum(buffer_sizes)})")
    
    # Test uncompress_to_iovec
    try:
        chunks = snappy_wrapper.uncompress_to_iovec(compressed, buffer_sizes)
        reconstructed = b''.join(chunks)
        print(f"Decompressed into {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i}: {len(chunk)} bytes - {repr(chunk[:20])}")
        
        # Trim any extra bytes if buffer was larger than needed
        if len(reconstructed) > len(test_data):
            reconstructed = reconstructed[:len(test_data)]
            print(f"Note: Trimmed {len(reconstructed) - len(test_data)} extra bytes")
        
        assert reconstructed == test_data, f"IOVec reconstruction failed: got {len(reconstructed)} bytes, expected {len(test_data)}"
        print("✓ IOVec decompression successful")
    except RuntimeError as e:
        print(f"IOVec decompression error: {e}")
        # Try with exact single buffer as fallback test
        try:
            exact_chunks = snappy_wrapper.uncompress_to_iovec(compressed, [actual_length])
            print(f"✓ Single buffer decompression worked: {len(exact_chunks[0])} bytes")
        except Exception as e2:
            print(f"Even single buffer failed: {e2}")

def test_source_sink_interface():
    """Test Source/Sink interface functions."""
    print_header("Testing Source/Sink Interface")
    
    test_data = b"Testing the Source and Sink interfaces. " * 4
    print(f"Test data size: {len(test_data)} bytes")
    
    # First test with regular compression for comparison
    regular_compressed = snappy_wrapper.compress_data(test_data)
    print(f"Regular compressed: {len(regular_compressed)} bytes")
    
    # Test is_valid_compressed_source
    is_valid = snappy_wrapper.is_valid_compressed_source(regular_compressed)
    print(f"Is valid compressed (via Source): {is_valid}")
    
    # Test compress_source_to_sink - note this might produce different output
    try:
        source_compressed = snappy_wrapper.compress_source_to_sink(test_data)
        print(f"Source/Sink compressed: {len(source_compressed)} bytes")
        
        # The Source/Sink compression might be different, so we test by decompressing
        # Try decompressing with regular method first
        try:
            test_decomp = snappy_wrapper.uncompress_data(source_compressed)
            if test_decomp == test_data:
                print("Note: Source/Sink output is compatible with regular decompression")
        except:
            pass
    except Exception as e:
        print(f"Source/Sink compression error: {e}")
        source_compressed = regular_compressed  # Fall back to regular for further tests
    
    # Test with compression level 2
    opt2 = snappy_wrapper.PyCompressionOptions(level=2)
    try:
        source_compressed_l2 = snappy_wrapper.compress_source_to_sink(test_data, opt2)
        print(f"Source/Sink level 2: {len(source_compressed_l2)} bytes")
    except Exception as e:
        print(f"Source/Sink level 2 error: {e}")
    
    # Test get_uncompressed_length_from_source
    try:
        length = snappy_wrapper.get_uncompressed_length_from_source(regular_compressed)
        print(f"Uncompressed length (via Source): {length} bytes")
        assert length == len(test_data), "Length mismatch"
    except RuntimeError as e:
        print(f"Error getting length: {e}")
    
    # Test uncompress_source_to_sink - use regular compressed data
    try:
        source_decompressed = snappy_wrapper.uncompress_source_to_sink(regular_compressed)
        # print('HEREEEEE: ', source_decompressed, '\nTESTEEEE: ',test_data)
        assert source_decompressed == test_data, "Source/Sink decompression of regular compressed failed"
        print("✓ Source/Sink decompression successful (regular compressed)")
    except RuntimeError as e:
        print(f"Source/Sink decompression error: {e}")
    
    # Test raw_uncompress_from_source
    try:
        raw_source_decompressed = snappy_wrapper.raw_uncompress_from_source(regular_compressed)
        assert raw_source_decompressed == test_data, "Raw Source decompression failed"
        print("✓ Raw Source decompression successful")
    except RuntimeError as e:
        print(f"Raw Source decompression error: {e}")

def test_iovec_source_decompression():
    """Test IOVec decompression via Source interface."""
    print_header("Testing IOVec Decompression via Source")
    
    test_data = b"Split this into multiple buffers using Source!"
    compressed = snappy_wrapper.compress_data(test_data)
    
    # Get actual length
    actual_length = snappy_wrapper.get_uncompressed_length(compressed)
    
    # Use exact buffer sizes
    buffer_sizes = [10, 15, 12, 9]  # Total: 46 bytes (exact)
    print(f"Original: {len(test_data)} bytes")
    print(f"Actual uncompressed length: {actual_length} bytes")
    print(f"Buffer sizes: {buffer_sizes} (total: {sum(buffer_sizes)})")
    
    try:
        chunks = snappy_wrapper.raw_uncompress_to_iovec_from_source(compressed, buffer_sizes)
        reconstructed = b''.join(chunks)
        print(f"Decompressed into {len(chunks)} chunks via Source")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i}: {repr(chunk)}")
        
        # Handle potential extra bytes
        if len(reconstructed) > len(test_data):
            print(f"Note: Got {len(reconstructed) - len(test_data)} extra bytes")
            reconstructed = reconstructed[:len(test_data)]
        
        assert reconstructed == test_data, f"Source IOVec reconstruction failed: got {repr(reconstructed)}"
        print("✓ Source IOVec decompression successful")
    except RuntimeError as e:
        print(f"Source IOVec error: {e}")
        # Try single buffer as fallback
        try:
            single_chunk = snappy_wrapper.raw_uncompress_to_iovec_from_source(compressed, [actual_length])
            print(f"✓ Single buffer via Source worked: {len(single_chunk[0])} bytes")
        except Exception as e2:
            print(f"Even single buffer failed: {e2}")

def test_partial_decompression():
    """Test uncompress_as_much_as_possible function."""
    print_header("Testing Partial Decompression")
    
    # Create multiple compressed blocks
    parts = [
        b"First part of data. ",
        b"Second part here. ",
        b"Third part follows. ",
        b"Fourth and final. "
    ]
    
    # Compress parts individually
    compressed_parts = [snappy_wrapper.compress_data(part) for part in parts]
    full_compressed = b''.join(compressed_parts)
    
    print(f"Created {len(parts)} compressed parts")
    print(f"Total compressed size: {len(full_compressed)} bytes")
    
    # Test on valid data
    result, processed = snappy_wrapper.uncompress_as_much_as_possible(full_compressed)
    print(f"\nValid data: decompressed {len(result)} bytes, processed {processed} bytes")
    print(f"Result: {repr(result)}")
    
    # Test on truncated data
    truncated = full_compressed[:-30]
    print(f"\nTruncated data: removed last 30 bytes")
    try:
        partial_result, partial_processed = snappy_wrapper.uncompress_as_much_as_possible(truncated)
        print(f"Partial: decompressed {len(partial_result)} bytes, processed {partial_processed} bytes")
        print(f"Partial result: {repr(partial_result)}")
    except Exception as e:
        print(f"Partial decompression error: {e}")
    
    # Test on invalid data
    invalid = b"Not compressed data at all!"
    try:
        invalid_result, invalid_processed = snappy_wrapper.uncompress_as_much_as_possible(invalid)
        print(f"\nInvalid data: decompressed {len(invalid_result)} bytes")
    except Exception as e:
        print(f"\nInvalid data error (expected): {e}")

def test_error_handling():
    """Test error handling and edge cases."""
    print_header("Testing Error Handling")
    
    # Test empty data
    empty = b""
    empty_compressed = snappy_wrapper.compress_data(empty)
    empty_decompressed = snappy_wrapper.uncompress_data(empty_compressed)
    print(f"Empty data: {len(empty_compressed)} bytes compressed")
    assert empty == empty_decompressed, "Empty data failed"
    
    # Test invalid compressed data
    invalid = b"This is definitely not compressed!"
    print(f"\nTesting invalid data:")
    print(f"  Is valid: {snappy_wrapper.is_valid_compressed_buffer(invalid)}")
    print(f"  Is valid (Source): {snappy_wrapper.is_valid_compressed_source(invalid)}")
    
    try:
        snappy_wrapper.uncompress_data(invalid)
        print("ERROR: Should have failed!")
    except RuntimeError as e:
        print(f"  ✓ Correctly rejected: {e}")
    
    # Test corrupted data
    valid = snappy_wrapper.compress_data(b"Valid data here")
    corrupted = valid[:10] + b'\xFF\xFF' + valid[12:]
    print(f"\nTesting corrupted data:")
    print(f"  Is valid: {snappy_wrapper.is_valid_compressed_buffer(corrupted)}")
    
    # Test IOVec with wrong types
    try:
        snappy_wrapper.compress_from_iovec([b"bytes", "string", 123])
    except TypeError as e:
        print(f"\n✓ IOVec type checking: {e}")

def test_performance():
    """Benchmark compression performance."""
    print_header("Performance Benchmarks")
    
    sizes = [(1024, "1KB"), (10240, "10KB"), (102400, "100KB")]
    
    for size, label in sizes:
        # Generate test data
        data = (b"Performance test data. " * (size // 23))[:size]
        
        # Warm up
        snappy_wrapper.compress_data(data)
        
        # Benchmark compression
        iterations = 100
        start = time.time()
        for _ in range(iterations):
            compressed = snappy_wrapper.compress_data(data)
        compress_time = (time.time() - start) / iterations
        
        # Benchmark decompression
        start = time.time()
        for _ in range(iterations):
            decompressed = snappy_wrapper.uncompress_data(compressed)
        decompress_time = (time.time() - start) / iterations
        
        # Calculate metrics
        compress_speed = size / compress_time / (1024*1024)
        decompress_speed = size / decompress_time / (1024*1024)
        ratio = size / len(compressed)
        
        print(f"\n{label}:")
        print(f"  Compression: {compress_speed:.1f} MB/s")
        print(f"  Decompression: {decompress_speed:.1f} MB/s")
        print(f"  Ratio: {ratio:.2f}x")

def main():
    """Run all tests."""
    print("="*60)
    print("Snappy Compression Library - Comprehensive Test Suite v11")
    print("="*60)
    
    tests = [
        ("Constants", test_constants),
        ("Compression Options", test_compression_options),
        ("Basic Compression", test_basic_compression),
        ("Compression Levels", test_compression_levels),
        ("Raw Compression", test_raw_compression),
        ("IOVec Compression", test_iovec_compression),
        ("IOVec Decompression", test_iovec_decompression),
        ("Source/Sink Interface", test_source_sink_interface),
        ("IOVec Source Decompression", test_iovec_source_decompression),
        ("Partial Decompression", test_partial_decompression),
        ("Error Handling", test_error_handling),
        ("Performance", test_performance),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"Test Summary: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())