
from snappywasm.core import SnappyWasm

def main():
    snappy = SnappyWasm()
    data = b"hello worldsajisijqbwnedjbideiwidjqbwdjhqwbdjbkdjjkdajksdjka" * 100
    compressed = snappy.compress(data, 2)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
