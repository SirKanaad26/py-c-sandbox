import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def main():
    snappy = SnappyWasm()
    
    # Create multiple data buffers to demonstrate IOVec compression
    data_buffers = [
        b"hello world ",
        b"this is a test ",
        b"of IOVec compression ",
        b"with multiple buffers " * 3,
        b"ending here."
    ]
    
    print("=== IOVec Compression Test ===")
    print(f"Number of buffers: {len(data_buffers)}")
    print(f"Buffer sizes: {[len(buf) for buf in data_buffers]}")
    
    # Calculate total original size
    total_original_size = sum(len(buf) for buf in data_buffers)
    print(f"Total original size: {total_original_size} bytes")
    
    try:
        # Compress using IOVec
        compressed_iovec = snappy.compress_from_iovec(data_buffers)
        print(f"IOVec compressed size: {len(compressed_iovec)} bytes")
        print(f"IOVec compression ratio: {(1 - len(compressed_iovec)/total_original_size)*100:.1f}%")
        
        # Verify the compressed data is valid
        is_valid = snappy.is_valid_compressed_buffer(compressed_iovec)
        print(f"Compressed data is valid: {is_valid}")
        
        # Decompress and verify integrity
        uncompressed = snappy.uncompress(compressed_iovec)
        expected_data = b"".join(data_buffers)
        integrity_check = expected_data == uncompressed
        print(f"Data integrity check: {'PASS' if integrity_check else 'FAIL'}")
        
        print("\n=== Comparison with Regular Compression ===")
        # Compare with regular compression of concatenated data
        regular_compressed = snappy.compress(expected_data)
        print(f"Regular compressed size: {len(regular_compressed)} bytes")
        print(f"Regular compression ratio: {(1 - len(regular_compressed)/total_original_size)*100:.1f}%")
        print(f"Size difference (IOVec - Regular): {len(compressed_iovec) - len(regular_compressed)} bytes")
        
        # Verify both methods produce identical results when decompressed
        regular_uncompressed = snappy.uncompress(regular_compressed)
        methods_match = uncompressed == regular_uncompressed
        print(f"Both methods produce identical output: {methods_match}")
        
    except RuntimeError as e:
        print(f"IOVec compression failed: {e}")
        print("Note: Ensure your WASM module includes the CompressFromIOVec function")
    
    print("\n=== Edge Case Tests ===")
    
    # Test with single buffer
    try:
        single_buffer = [b"single buffer test " * 5]
        single_compressed = snappy.compress_from_iovec(single_buffer)
        single_uncompressed = snappy.uncompress(single_compressed)
        single_check = single_buffer[0] == single_uncompressed
        print(f"Single buffer test: {'PASS' if single_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Single buffer test failed: {e}")
    
    # Test with mixed buffer types
    try:
        mixed_buffers = [
            b"bytes type buffer",
            bytearray(b"bytearray type buffer"),
            b"final bytes buffer"
        ]
        mixed_compressed = snappy.compress_from_iovec(mixed_buffers)
        mixed_uncompressed = snappy.uncompress(mixed_compressed)
        mixed_expected = b"".join(mixed_buffers)
        mixed_check = mixed_expected == mixed_uncompressed
        print(f"Mixed buffer types test: {'PASS' if mixed_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Mixed buffer types test failed: {e}")
    
    # Test with empty list
    try:
        empty_compressed = snappy.compress_from_iovec([])
        print(f"Empty buffer list result: {len(empty_compressed)} bytes")
    except RuntimeError as e:
        print(f"Empty buffer list test failed: {e}")

if __name__ == "__main__":
    main()