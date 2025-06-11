import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def main():
    snappy = SnappyWasm()
    data = b"hello world " * 10
    compressed = snappy.compress(data)
    print(compressed)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
