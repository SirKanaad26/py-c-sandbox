import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/snappywasm')
# from snappywasm.snappy_sandbox import SnappyWasm
from snappywasm.snappy_sandbox_framework import SnappyWasm

def main():
    snappy = SnappyWasm()
    
    print("=== Raw IOVec Decompression Test ===")
    
    original_data_parts = [
        b"First chunk of data " * 5,      # 100 bytes
        b"Second part is longer " * 8,    # 184 bytes  
        b"Third section " * 3,            # 45 bytes
        b"Final piece " * 2,              # 24 bytes
        b"End"                            # 3 bytes
    ]
    
    buffer_sizes = [len(part) for part in original_data_parts]
    total_size = sum(buffer_sizes)
    
    print(f"Original data parts: {len(original_data_parts)}")
    print(f"Buffer sizes: {buffer_sizes}")
    print(f"Total size: {total_size} bytes")
    
    original_combined = b"".join(original_data_parts)
    compressed_data = snappy.compress(original_combined)
    
    print(f"Compressed size: {len(compressed_data)} bytes")
    print(f"Compression ratio: {(1 - len(compressed_data)/total_size)*100:.1f}%")
    
    try:
        print("\n=== Testing Raw IOVec Decompression ===")
        
        decompressed_buffers = snappy.raw_uncompress_to_iovec(compressed_data, buffer_sizes)
        
        print(f"Successfully decompressed into {len(decompressed_buffers)} separate buffers")
        
        all_match = True
        for i, (original, decompressed) in enumerate(zip(original_data_parts, decompressed_buffers)):
            match = original == decompressed
            print(f"Buffer {i+1}: {len(decompressed)} bytes - {'MATCH' if match else 'MISMATCH'}")
            if not match:
                all_match = False
                print(f"  Expected: {original[:20]}...")
                print(f"  Got:      {decompressed[:20]}...")
        
        print(f"\nOverall integrity check: {'PASS' if all_match else 'FAIL'}")
        
        reconstructed = b"".join(decompressed_buffers)
        total_match = reconstructed == original_combined
        print(f"Total data integrity: {'PASS' if total_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Raw IOVec decompression failed: {e}")
        return
    
    print("\n=== Performance Comparison ===")
    
    try:
        regular_decompressed = snappy.uncompress(compressed_data)
        regular_match = regular_decompressed == original_combined
        print(f"Regular decompression: {'PASS' if regular_match else 'FAIL'}")
        print("IOVec advantage: Direct scatter-gather decompression avoids intermediate copying")
        
    except RuntimeError as e:
        print(f"Regular decompression failed: {e}")
    
    print("\n=== Edge Case Tests ===")
    try:
        single_data = b"Single buffer test data " * 10
        single_compressed = snappy.compress(single_data)
        single_result = snappy.raw_uncompress_to_iovec(single_compressed, [len(single_data)])
        
        single_match = single_result[0] == single_data
        print(f"Single buffer test: {'PASS' if single_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Single buffer test failed: {e}")
    
    try:
        varied_data = [
            b"A" * 1,           # Very small
            b"B" * 100,         # Medium
            b"C" * 1000,        # Large
            b"D" * 10,          # Small again
        ]
        varied_combined = b"".join(varied_data)
        varied_compressed = snappy.compress(varied_combined)
        varied_sizes = [len(chunk) for chunk in varied_data]
        
        varied_result = snappy.raw_uncompress_to_iovec(varied_compressed, varied_sizes)
        
        varied_match = all(orig == decomp for orig, decomp in zip(varied_data, varied_result))
        print(f"Varied buffer sizes test: {'PASS' if varied_match else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"Varied buffer sizes test failed: {e}")
    
    try:
        wrong_sizes = [50, 50, 50]  # Wrong total size
        snappy.raw_uncompress_to_iovec(compressed_data, wrong_sizes)
        print("Buffer size mismatch test: FAIL (should have raised error)")
    except RuntimeError as e:
        print(f"Buffer size mismatch test: PASS (correctly failed: {e})")
    
    # Test empty buffer list
    try:
        empty_result = snappy.raw_uncompress_to_iovec(b"", [])
        print(f"Empty buffer list test: {'PASS' if empty_result == [] else 'FAIL'}")
    except RuntimeError as e:
        print(f"Empty buffer list test failed: {e}")
    
    print("\n=== Use Case Examples ===")
    
    print("Example 1: Network packet reconstruction")
    try:
        header = b"PKT_HDR_V1" + b"\x00" * 6   # 16 bytes
        payload1 = b"Important data chunk 1 " * 4  # 92 bytes
        payload2 = b"Critical information " * 5    # 100 bytes
        checksum = b"CHKSUM"                       # 6 bytes
        
        packet_parts = [header, payload1, payload2, checksum]
        packet_data = b"".join(packet_parts)
        packet_compressed = snappy.compress(packet_data)
        packet_sizes = [len(part) for part in packet_parts]
        
        reconstructed_parts = snappy.raw_uncompress_to_iovec(packet_compressed, packet_sizes)
        
        print(f"  Reconstructed packet with {len(reconstructed_parts)} parts")
        print(f"  Header: {reconstructed_parts[0][:10]}...")
        print(f"  Payload1 size: {len(reconstructed_parts[1])}")
        print(f"  Payload2 size: {len(reconstructed_parts[2])}")
        print(f"  Checksum: {reconstructed_parts[3]}")
        
    except RuntimeError as e:
        print(f"  Network packet example failed: {e}")
    
    print("\nExample 2: Database record field separation")
    try:
        record_id = b"12345678"        # 8 bytes
        name_field = b"John Doe" + b" " * 25   # 32 bytes (padded)
        data_field = b"Some important data here" + b" " * 10  # 33 bytes
        timestamp = b"2025-05-29T10:30:00Z"  # 20 bytes
        
        record_parts = [record_id, name_field, data_field, timestamp]
        record_data = b"".join(record_parts)
        record_compressed = snappy.compress(record_data)
        record_sizes = [len(part) for part in record_parts]
        
        field_data = snappy.raw_uncompress_to_iovec(record_compressed, record_sizes)
        
        print(f"  Record ID: {field_data[0].decode().strip()}")
        print(f"  Name: {field_data[1].decode().strip()}")
        print(f"  Data: {field_data[2].decode().strip()}")
        print(f"  Timestamp: {field_data[3].decode()}")
        
    except RuntimeError as e:
        print(f"  Database record example failed: {e}")

if __name__ == "__main__":
    main()