import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def test_raw_compress(snappy):
    """Test the raw compression functionality"""
    print("=" * 60)
    print("Testing Raw Compression Functions")
    print("=" * 60)
    
    # Test data of various sizes and types
    test_cases = [
        b"A" * 100,  # Highly compressible
        b"The quick brown fox jumps over the lazy dog. " * 50,
        bytes(range(256)) * 2,  # Mixed data
        b"x",  # Single byte
    ]
    
    for i, test_data in enumerate(test_cases):
        print(f"\nTest Case {i + 1}:")
        print(f"Original size: {len(test_data)} bytes")
        
        if len(test_data) > 100:
            print(f"Data preview: {test_data[:50]}...{test_data[-50:]}")
        else:
            print(f"Data: {test_data}")
        
        # Test basic raw compression
        try:
            compressed = snappy.raw_compress(test_data)
            if compressed:
                compression_ratio = (1 - len(compressed) / max(len(test_data), 1)) * 100
                print(f"✓ Raw compress successful: {len(compressed)} bytes ({compression_ratio:.1f}% reduction)")
                
                # Verify we can decompress it back
                try:
                    # Create buffer for decompression
                    uncompressed_buffer = bytearray(len(test_data))
                    success = snappy.raw_uncompress(compressed, uncompressed_buffer)
                    
                    if success and bytes(uncompressed_buffer) == test_data:
                        print("✓ Round-trip verification: PASS")
                    else:
                        print("✗ Round-trip verification: FAIL")
                        
                except Exception as e:
                    print(f"✗ Decompression failed: {e}")
                    
            else:
                print("✗ Raw compress failed")
                
        except Exception as e:
            print(f"✗ Raw compress error: {e}")
        
        # Test compression with options (different levels)
        for level in [1, 2]:
            try:
                compressed_with_opts = snappy.raw_compress_with_options(test_data, level)
                if compressed_with_opts:
                    compression_ratio = (1 - len(compressed_with_opts) / max(len(test_data), 1)) * 100
                    print(f"✓ Raw compress (level {level}): {len(compressed_with_opts)} bytes ({compression_ratio:.1f}% reduction)")
                else:
                    print(f"✗ Raw compress with level {level} failed")
                    
            except Exception as e:
                print(f"✗ Raw compress with level {level} error: {e}")


def benchmark_compression_methods(snappy):
    """Compare different compression methods"""
    print("\n" + "=" * 60)
    print("Benchmarking Compression Methods")
    print("=" * 60)
    
    # Create test data
    test_data = b"The quick brown fox jumps over the lazy dog. " * 50
    print(f"Test data size: {len(test_data)} bytes")
    
    methods = [
        ("Standard compress", lambda: snappy.compress(test_data)),
        ("Raw compress", lambda: snappy.raw_compress(test_data)),
        ("Raw compress (level 1)", lambda: snappy.raw_compress_with_options(test_data, 1)),
        ("Raw compress (level 2)", lambda: snappy.raw_compress_with_options(test_data, 2)),
    ]
    
    import time
    
    for method_name, method_func in methods:
        try:
            start_time = time.time()
            result = method_func()
            end_time = time.time()
            
            if result:
                compression_ratio = (1 - len(result) / len(test_data)) * 100
                duration_ms = (end_time - start_time) * 1000
                print(f"{method_name:<25}: {len(result):>6} bytes ({compression_ratio:>5.1f}% reduction) in {duration_ms:.2f}ms")
            else:
                print(f"{method_name:<25}: FAILED")
                
        except Exception as e:
            print(f"{method_name:<25}: ERROR - {e}")


if __name__ == "__main__":
    # This would be called with your actual snappy instance
    # Example usage:
    snappy = SnappyWasm()
    test_raw_compress(snappy)
    benchmark_compression_methods(snappy)
    
    print("Raw compression test script ready.")
    print("Import this module and call the test functions with your snappy instance.")
    print("\nExample usage:")
    print("  from raw_compress_test import test_raw_compress")
    print("  test_raw_compress(your_snappy_instance)")