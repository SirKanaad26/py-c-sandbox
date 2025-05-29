
from snappywasm.core import SnappyWasm

def main():
    snappy = SnappyWasm()
    data = b"hello world " * 100
    compressed = snappy.compress(data,1)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
