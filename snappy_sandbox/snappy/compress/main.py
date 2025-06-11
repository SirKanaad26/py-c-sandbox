import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/snappywasm')
# from snappywasm.snappy_sandbox import SnappyWasm
from snappywasm.snappy_sandbox_framework import SnappyWasm


def main():
    snappy = SnappyWasm()
    data = b"hello world " * 10
    compressed = snappy.compress(data)
    print(compressed)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
