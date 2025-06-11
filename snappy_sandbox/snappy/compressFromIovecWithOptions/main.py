import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm


class SnappyCompressFromIOVecWithOptionsTester:
    def __init__(self):
        self.snappy = SnappyWasm()
    
    def create_test_data(self):
        return [
            b"hello world ",
            b"this is a test ",
            b"of IOVec compression ",
            b"with multiple buffers " * 3,
            b"ending here."
        ]
    
    def print_test_info(self, data_buffers):
        print("=== IOVec Compression Test ===")
        print(f"Number of buffers: {len(data_buffers)}")
        print(f"Buffer sizes: {[len(buf) for buf in data_buffers]}")
        
        total_size = sum(len(buf) for buf in data_buffers)
        print(f"Total original size: {total_size} bytes")
        return total_size
    
    def test_iovec_compression(self, data_buffers, total_size, compression_level=2):
        try:
            compressed_iovec = self.snappy.compress_from_iovec(data_buffers, compression_level)
            print(f"IOVec compressed size: {len(compressed_iovec)} bytes")
            print(f"IOVec compression ratio: {(1 - len(compressed_iovec)/total_size)*100:.1f}%")
            
            is_valid = self.snappy.is_valid_compressed_buffer(compressed_iovec)
            print(f"Compressed data is valid: {is_valid}")
            
            uncompressed = self.snappy.uncompress(compressed_iovec)
            expected_data = b"".join(data_buffers)
            integrity_check = expected_data == uncompressed
            print(f"Data integrity check: {'PASS' if integrity_check else 'FAIL'}")
            
            return compressed_iovec, uncompressed, expected_data
        except RuntimeError as e:
            print(f"IOVec compression failed: {e}")
            print("Note: Ensure your WASM module includes the CompressFromIOVec function")
            return None, None, None
    
    def compare_with_regular_compression(self, expected_data, uncompressed, total_size, compressed_iovec):
        print("\n=== Comparison with Regular Compression ===")
        regular_compressed = self.snappy.compress(expected_data)
        print(f"Regular compressed size: {len(regular_compressed)} bytes")
        print(f"Regular compression ratio: {(1 - len(regular_compressed)/total_size)*100:.1f}%")
        
        if compressed_iovec is not None:
            print(f"Size difference (IOVec - Regular): {len(compressed_iovec) - len(regular_compressed)} bytes")
            
            regular_uncompressed = self.snappy.uncompress(regular_compressed)
            methods_match = uncompressed == regular_uncompressed
            print(f"Both methods produce identical output: {methods_match}")
    
    def test_single_buffer(self):
        try:
            single_buffer = [b"single buffer test " * 5]
            single_compressed = self.snappy.compress_from_iovec(single_buffer)
            single_uncompressed = self.snappy.uncompress(single_compressed)
            single_check = single_buffer[0] == single_uncompressed
            print(f"Single buffer test: {'PASS' if single_check else 'FAIL'}")
        except RuntimeError as e:
            print(f"Single buffer test failed: {e}")
    
    def test_mixed_buffer_types(self):
        try:
            mixed_buffers = [
                b"bytes type buffer",
                bytearray(b"bytearray type buffer"),
                b"final bytes buffer"
            ]
            mixed_compressed = self.snappy.compress_from_iovec(mixed_buffers)
            mixed_uncompressed = self.snappy.uncompress(mixed_compressed)
            mixed_expected = b"".join(mixed_buffers)
            mixed_check = mixed_expected == mixed_uncompressed
            print(f"Mixed buffer types test: {'PASS' if mixed_check else 'FAIL'}")
        except RuntimeError as e:
            print(f"Mixed buffer types test failed: {e}")
    
    def test_empty_buffer_list(self):
        try:
            empty_compressed = self.snappy.compress_from_iovec([])
            print(f"Empty buffer list result: {len(empty_compressed)} bytes")
        except RuntimeError as e:
            print(f"Empty buffer list test failed: {e}")
    
    def run_edge_case_tests(self):
        print("\n=== Edge Case Tests ===")
        self.test_single_buffer()
        self.test_mixed_buffer_types()
        self.test_empty_buffer_list()
    
    def run_all_tests(self):
        data_buffers = self.create_test_data()
        total_size = self.print_test_info(data_buffers)
        
        compressed_iovec, uncompressed, expected_data = self.test_iovec_compression(data_buffers, total_size, 2)
        
        if expected_data is not None:
            self.compare_with_regular_compression(expected_data, uncompressed, total_size, compressed_iovec)
        
        self.run_edge_case_tests()


def main():
    tester = SnappyCompressFromIOVecWithOptionsTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()