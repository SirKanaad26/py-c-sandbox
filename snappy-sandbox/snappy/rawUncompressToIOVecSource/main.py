import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm

def main():
    snappy = SnappyWasm()
    
    print("=== Raw IOVec Decompression from Source Test ===")
    
    # Create test data with different characteristics
    original_data_parts = [
        b"Header: " + b"H" * 32,           # 40 bytes - header
        b"Metadata: " + b"M" * 64,        # 73 bytes - metadata  
        b"Payload: " + b"P" * 200,        # 209 bytes - main payload
        b"Footer: " + b"F" * 16,          # 24 bytes - footer
        b"Checksum: " + b"C" * 8          # 17 bytes - checksum
    ]
    
    # Calculate expected buffer sizes for decompression
    buffer_sizes = [len(part) for part in original_data_parts]
    total_size = sum(buffer_sizes)
    
    print(f"Original data structure:")
    for i, (part, size) in enumerate(zip(original_data_parts, buffer_sizes)):
        print(f"  Part {i+1}: {size} bytes - {part[:20].decode('utf-8', errors='ignore')}...")
    print(f"Total size: {total_size} bytes")
    
    # Create compressed data by joining all parts and compressing
    original_combined = b"".join(original_data_parts)
    compressed_data = snappy.compress(original_combined)
    
    print(f"Compressed size: {len(compressed_data)} bytes")
    print(f"Compression ratio: {(1 - len(compressed_data)/total_size)*100:.1f}%")
    
    try:
        print("\n=== Testing Raw IOVec Decompression from Source ===")
        
        # Use raw_uncompress_to_iovec_from_source to decompress into separate buffers
        decompressed_buffers = snappy.raw_uncompress_to_iovec_from_source(compressed_data, buffer_sizes)
        
        print(f"Successfully decompressed into {len(decompressed_buffers)} separate buffers using Source abstraction")
        
        # Verify each buffer matches the original
        all_match = True
        for i, (original, decompressed) in enumerate(zip(original_data_parts, decompressed_buffers)):
            match = original == decompressed
            print(f"Buffer {i+1}: {len(decompressed)} bytes - {'MATCH' if match else 'MISMATCH'}")
            if not match:
                all_match = False
                print(f"  Expected: {original[:30]}...")
                print(f"  Got:      {decompressed[:30]}...")
        
        print(f"\nOverall integrity check: {'PASS' if all_match else 'FAIL'}")
        
        # Verify total reconstructed data matches original
        reconstructed = b"".join(decompressed_buffers)
        total_match = reconstructed == original_combined
        print(f"Total data integrity: {'PASS' if total_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Raw IOVec decompression from source failed: {e}")
        print("Note: Ensure your WASM module includes the RawUncompressToIOVecFromSource function")
        return
    
    print("\n=== Comparison with Direct IOVec Method ===")
    
    # Compare with the direct raw_uncompress_to_iovec method if available
    try:
        if hasattr(snappy, 'raw_uncompress_to_iovec'):
            direct_decompressed = snappy.raw_uncompress_to_iovec(compressed_data, buffer_sizes)
            
            # Compare results
            methods_match = all(src == direct for src, direct in zip(decompressed_buffers, direct_decompressed))
            print(f"Source vs Direct method results match: {'YES' if methods_match else 'NO'}")
        else:
            print("Direct IOVec method not available for comparison")
            
    except RuntimeError as e:
        print(f"Direct IOVec method comparison failed: {e}")
    
    print("\n=== Performance and Use Case Tests ===")
    
    # Test with larger, more realistic data
    try:
        # Simulate a compressed log file with structured entries
        log_entries = [
            b"2025-05-29 10:30:00 INFO ",      # 20 bytes - timestamp
            b"user:john.doe@example.com ",     # 24 bytes - user
            b"action:file_upload ",            # 17 bytes - action
            b"file:document.pdf size:2048KB ", # 28 bytes - details
            b"status:success duration:150ms"   # 27 bytes - result
        ]
        
        log_data = b"".join(log_entries)
        log_compressed = snappy.compress(log_data)
        log_sizes = [len(entry) for entry in log_entries]
        
        parsed_log = snappy.raw_uncompress_to_iovec_from_source(log_compressed, log_sizes)
        
        print("Log parsing example:")
        print(f"  Timestamp: {parsed_log[0].decode().strip()}")
        print(f"  User: {parsed_log[1].decode().strip()}")
        print(f"  Action: {parsed_log[2].decode().strip()}")
        print(f"  Details: {parsed_log[3].decode().strip()}")
        print(f"  Result: {parsed_log[4].decode().strip()}")
        
        log_match = all(orig == parsed for orig, parsed in zip(log_entries, parsed_log))
        print(f"  Log parsing accuracy: {'PASS' if log_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Log parsing example failed: {e}")
    
    print("\n=== Edge Cases and Error Handling ===")
    
    # Test with single buffer
    try:
        single_data = b"Single buffer test with Source abstraction " * 5
        single_compressed = snappy.compress(single_data)
        single_result = snappy.raw_uncompress_to_iovec_from_source(single_compressed, [len(single_data)])
        
        single_match = single_result[0] == single_data
        print(f"Single buffer with Source test: {'PASS' if single_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Single buffer test failed: {e}")
    
    # Test with very small buffers
    try:
        tiny_parts = [b"A", b"B", b"C", b"D", b"E"]  # 1 byte each
        tiny_combined = b"".join(tiny_parts)
        tiny_compressed = snappy.compress(tiny_combined)
        tiny_sizes = [1] * 5
        
        tiny_result = snappy.raw_uncompress_to_iovec_from_source(tiny_compressed, tiny_sizes)
        tiny_match = all(orig == result for orig, result in zip(tiny_parts, tiny_result))
        print(f"Tiny buffers test: {'PASS' if tiny_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Tiny buffers test failed: {e}")
    
    # Test buffer size validation
    try:
        wrong_sizes = [10, 20, 30]  # Wrong total size
        snappy.raw_uncompress_to_iovec_from_source(compressed_data, wrong_sizes)
        print("Buffer size validation test: FAIL (should have raised error)")
    except RuntimeError as e:
        print(f"Buffer size validation test: PASS (correctly failed)")
    
    # Test empty buffer list
    try:
        empty_result = snappy.raw_uncompress_to_iovec_from_source(b"", [])
        print(f"Empty buffer list test: {'PASS' if empty_result == [] else 'FAIL'}")
    except RuntimeError as e:
        print(f"Empty buffer list test: Exception raised - {e}")
    
    print("\n=== Source Abstraction Benefits ===")
    print("The Source abstraction provides:")
    print("- Unified interface for different input types (byte arrays, files, etc.)")
    print("- Better memory management for large compressed data")
    print("- Consistent API across different Snappy decompression functions")
    print("- Potential for streaming decompression in future implementations")

if __name__ == "__main__":
    main()