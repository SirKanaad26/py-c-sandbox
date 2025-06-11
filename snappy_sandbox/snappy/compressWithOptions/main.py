import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm


class SnappyCompressWithOptionsTester:
    def __init__(self):
        self.snappy = SnappyWasm()
    
    def create_test_data(self):
        return b"hello worldsajisijqbwnedjbideiwidjqbwdjhqwbdjbkdjjkdajksdjka" * 50
    
    def test_compression_with_level(self, data, compression_level=2):
        compressed = self.snappy.compress(data, compression_level)
        return compressed
    
    def display_results(self, compressed, original_data):
        print("=== Level Compression Test ===")
        print(f"Original size: {len(original_data)} bytes")
        print(f"Compressed size: {len(compressed)} bytes")
        print(f"Compression ratio: {(1 - len(compressed)/len(original_data))*100:.1f}%")
    
    def run_all_tests(self):
        data = self.create_test_data()
        compressed = self.test_compression_with_level(data, 2)
        self.display_results(compressed, data)


def main():
    tester = SnappyCompressWithOptionsTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()