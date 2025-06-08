import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm

def test_compress_source_sink():
    """Test the compress_source_sink method"""
    
    # Initialize SnappyWasm
    snappy = SnappyWasm()
    
    # Prepare test data
    test_string = "Hello, Snappy compression!"
    test_bytes = test_string.encode('utf-8')
    input_size = len(test_bytes)
    
    print(f"Testing CompressFromSourceToSink...")
    print(f"Original data: '{test_string}'")
    print(f"Original size: {input_size} bytes")
    
    try:
        # Call the compression function
        compressed_data = snappy.compress_source_sink(test_string)
        compressed_size = len(compressed_data)
        
        if compressed_size > 0:
            print(f"✅ Compression successful!")
            print(f"   Compressed size: {compressed_size} bytes")
            print(f"   Compression ratio: {(1 - compressed_size/input_size)*100:.1f}%")
            
            # Test with bytes input too
            compressed_bytes = snappy.compress_source_sink(test_bytes)
            if compressed_data == compressed_bytes:
                print(f"✅ String and bytes input produce identical results")
            else:
                print(f"⚠️  String and bytes input produce different results")
                
        else:
            print("❌ Compression failed")
            
    except Exception as e:
        print(f"❌ Compression failed with error: {e}")

def test_multiple_data_sizes():
    """Test compression with different data sizes"""
    
    snappy = SnappyWasm()
    
    test_cases = [
        "A",  # Very small
        "Hello, World!",  # Small
        "Hello, Snappy compression! " * 10,  # Medium
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50,  # Large
    ]
    
    print(f"\n--- Testing Multiple Data Sizes ---")
    
    for i, test_data in enumerate(test_cases):
        print(f"\nTest {i+1}: {len(test_data)} bytes")
        print(f"Data preview: '{test_data[:50]}{'...' if len(test_data) > 50 else ''}'")
        
        try:
            compressed = snappy.compress_source_sink(test_data)
            ratio = (1 - len(compressed)/len(test_data)) * 100
            print(f"   Result: {len(test_data)} → {len(compressed)} bytes ({ratio:.1f}% reduction)")
            
        except Exception as e:
            print(f"   Failed: {e}")

if __name__ == "__main__":
    test_compress_source_sink()
    test_multiple_data_sizes()