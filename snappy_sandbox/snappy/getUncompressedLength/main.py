import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm


class SnappyGetUncompressedLengthTester:
    def __init__(self):
        self.snappy = SnappyWasm()
    
    def create_test_data(self):
        return b"hello world " * 10
    
    def test_compression_and_length_recovery(self, data):
        compressed = self.snappy.compress(data)
        recovered_length = self.snappy.get_uncompressed_length(compressed)
        return compressed, recovered_length
    
    def display_results(self, data, compressed, recovered_length):
        print("=== Uncompressed Length Recovery Test ===")
        print(f"Original size: {len(data)} bytes")
        print(f"Compressed size: {len(compressed)} bytes")
        print(f"Recovered size: {recovered_length} bytes")
        
        if recovered_length == len(data):
            print("Length recovery: PASS")
        else:
            print("Length recovery: FAIL")
        
        compression_ratio = (1 - len(compressed)/len(data))*100
        print(f"Compression ratio: {compression_ratio:.1f}%")
    
    def run_all_tests(self):
        data = self.create_test_data()
        compressed, recovered_length = self.test_compression_and_length_recovery(data)
        self.display_results(data, compressed, recovered_length)


def main():
    tester = SnappyGetUncompressedLengthTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()