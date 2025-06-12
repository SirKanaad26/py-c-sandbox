import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/snappywasm')
from snappywasm.snappy_sandbox import SnappyWasm
# from snappywasm.snappy_sandbox_framework import SnappyWasm

def test_raw_compress(snappy):
    """Test the raw compression functionality"""
    print("=" * 60)
    print("Testing Raw Compression Functions")
    print("=" * 60)
    
    test_cases = [
        b"A" * 100,
        b"The quick brown fox jumps over the lazy dog. " * 50,
        bytes(range(256)) * 2,  
        # b"x",  
    ]
    
    for i, test_data in enumerate(test_cases):
        print(f"\nTest Case {i + 1}:")
        print(f"Original size: {len(test_data)} bytes")
        
        # if len(test_data) > 100:
        #     print(f"Data preview: {test_data[:50]}...{test_data[-50:]}")
        # else:
        #     print(f"Data: {test_data}")
        
        try:
            compressed = snappy.raw_compress(test_data)
            if compressed:
                compression_ratio = (1 - len(compressed) / max(len(test_data), 1)) * 100
                print(f"Raw compress successful: {len(compressed)} bytes ({compression_ratio:.1f}% reduction)")
                
                try:
                    uncompressed_buffer = bytearray(len(test_data))
                    success = snappy.raw_uncompress(compressed, uncompressed_buffer)
                    # print('Here',success, uncompressed_buffer, test_data)
                    if bytes(uncompressed_buffer) == test_data:
                        print("Round-trip verification: PASS")
                    else:
                        print("Round-trip verification: FAIL")
                        
                except Exception as e:
                    print(f"Decompression failed: {e}")
                    
            else:
                print("Raw compress failed")
                
        except Exception as e:
            print(f"Raw compress error: {e}")



def benchmark_compression_methods(snappy):
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
    snappy = SnappyWasm()
    test_raw_compress(snappy)
    
    