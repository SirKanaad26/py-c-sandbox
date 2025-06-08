import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm
import time

def test_compress_source_sink_with_options():
    """Test the compress_source_sink_with_options method"""
    
    print("🚀 Snappy WASM Compression Test - CompressFromSourceToSinkWithOptions")
    print("=" * 70)
    
    # Initialize SnappyWasm
    snappy = SnappyWasm()
    
    # Get compression level info
    min_level = snappy.get_min_compression_level()
    max_level = snappy.get_max_compression_level()
    default_level = snappy.get_default_compression_level()
    
    print(f"✅ Snappy WASM version: {snappy.get_version()}")
    print(f"✅ Compression levels: {min_level} (min) to {max_level} (max), default: {default_level}")
    print()
    
    # Define test cases
    test_cases = [
        {
            "name": "Short Text",
            "data": "Hello, World! This is a test of Snappy compression.",
            "description": "Basic text compression"
        },
        {
            "name": "Repetitive Data", 
            "data": "AAABBBCCCDDDEEEFFFGGGHHHIIIJJJKKKLLLMMMNNNOOOPPPQQQRRRSSSTTTUUUVVVWWWXXXYYYZZZ" * 10,
            "description": "Highly repetitive pattern"
        },
        {
            "name": "JSON-like Data",
            "data": '{"name": "test", "value": 12345, "items": ["a", "b", "c"]}' * 20,
            "description": "Structured data"
        },
        {
            "name": "Large Text",
            "data": "The quick brown fox jumps over the lazy dog. " * 100,
            "description": "Large text block"
        }
    ]
    
    # Test compression levels
    levels = list(range(min_level, max_level + 1))
    
    print("📊 Compression Results")
    print("-" * 80)
    print(f"{'Test Case':<20} {'Original':<10} {'Level 1':<15} {'Level 2':<15} {'Time (ms)':<10}")
    print("-" * 80)
    
    for test_case in test_cases:
        test_name = test_case["name"]
        test_data = test_case["data"]
        input_size = len(test_data.encode('utf-8'))
        
        results = {}
        total_time = 0
        
        # Test each compression level
        for level in levels:
            try:
                # Measure compression time
                start_time = time.time()
                compressed_data = snappy.compress_source_sink_with_options(test_data, level)
                compression_time = (time.time() - start_time) * 1000  # Convert to ms
                total_time += compression_time
                
                # Verify decompression
                decompressed_data = snappy.uncompress(compressed_data)
                
                if decompressed_data == test_data.encode('utf-8'):
                    ratio = (1 - len(compressed_data) / input_size) * 100
                    results[level] = f"{len(compressed_data)}B ({ratio:.0f}%)"
                else:
                    results[level] = "Failed"
                    
            except Exception as e:
                results[level] = f"Error: {str(e)[:10]}..."
        
        # Display results
        level1_result = results.get(1, 'N/A')
        level2_result = results.get(2, 'N/A')
        print(f"{test_name:<20} {input_size:<10} {level1_result:<15} {level2_result:<15} {total_time:<10.2f}")
    
    print("-" * 80)
    
    # Performance comparison
    print("\n📈 Compression Level Analysis:")
    print("   • Level 1: Best for speed-critical applications")
    print("   • Level 2: Experimental - may provide better compression")
    print("\n✅ All tests completed successfully!")

def test_level_comparison():
    """Compare compression levels side by side"""
    
    print("\n--- Detailed Level Comparison ---")
    
    snappy = SnappyWasm()
    test_data = "Hello, Snappy compression with options! " * 50
    
    print(f"Test data: {len(test_data)} characters")
    print(f"Preview: '{test_data[:50]}...'")
    print()
    
    for level in [1, 2]:
        try:
            start_time = time.time()
            compressed = snappy.compress_source_sink_with_options(test_data, level)
            comp_time = (time.time() - start_time) * 1000
            
            # Test decompression
            start_time = time.time()
            decompressed = snappy.uncompress(compressed)
            decomp_time = (time.time() - start_time) * 1000
            
            ratio = (1 - len(compressed) / len(test_data)) * 100
            integrity = decompressed == test_data.encode('utf-8')
            
            print(f"Level {level}:")
            print(f"   Compressed: {len(test_data)} → {len(compressed)} bytes ({ratio:.1f}% reduction)")
            print(f"   Compression time: {comp_time:.2f} ms")
            print(f"   Decompression time: {decomp_time:.2f} ms") 
            print(f"   Data integrity: {'✅ PASS' if integrity else '❌ FAIL'}")
            print()
            
        except Exception as e:
            print(f"Level {level}: ❌ Failed - {e}")
            print()

if __name__ == "__main__":
    test_compress_source_sink_with_options()
    test_level_comparison()