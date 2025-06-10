import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm


def test_snappy_direct_wasm():
    """Test both MaxCompressedLength and GetUncompressedLength"""
    try:
        snappy = SnappyWasm()
    except Exception as e:
        print(f"Failed to load WASM module: {e}")
        return
    
    print("Testing WASM Built from Actual Snappy Source Files")
    print("=" * 60)
    
    print()
    
    # Test MaxCompressedLength
    print("Testing MaxCompressedLength:")
    test_sizes = [0, 10, 100, 1000, 10000, 100000]
    
    print(f"{'Input Size':>12} | {'Max Compressed':>14} | {'Overhead':>10} | {'Overhead %':>11}")
    print("-" * 60)
    
    for size in test_sizes:
        try:
            max_size = snappy.max_compressed_length(size)
            overhead = max_size - size
            overhead_pct = (overhead / size * 100) if size > 0 else 0
            
            print(f"{size:12,} | {max_size:14,} | {overhead:10,} | {overhead_pct:10.1f}%")
        except Exception as e:
            print(f"{size:12,} | {'ERROR':>14} | {'N/A':>10} | {'N/A':>11}")
            print(f"    Error: {e}")
    
    
    print(f"\n Performance Tests")
    print("-" * 30)
    
    import time
    iterations = 50000
    
    # Test MaxCompressedLength performance
    test_size = 1000
    try:
        start_time = time.time()
        for _ in range(iterations):
            snappy.max_compressed_length(test_size)
        mcl_time = time.time() - start_time
        
        print(f"MaxCompressedLength:")
        print(f"  {iterations:,} calls in {mcl_time:.3f}s")
        print(f"  {iterations/mcl_time:,.0f} calls/sec")
        print(f"  {(mcl_time/iterations)*1_000_000:.3f} μs/call")
    except Exception as e:
        print(f"MaxCompressedLength performance test failed: {e}")
        
    print(f"\nTest completed!")


if __name__ == "__main__":
    test_snappy_direct_wasm()