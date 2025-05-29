
from snappywasm.core import SnappyWasm

def main():
    snappy = SnappyWasm()
    data = b"Hello Worldadsf"
    data += data
    compressed = snappy.compress(data,compression_level=1)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
