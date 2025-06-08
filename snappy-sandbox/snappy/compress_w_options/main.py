import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm

def main():
    snappy = SnappyWasm()
    data = b"hello worldsajisijqbwnedjbideiwidjqbwdjhqwbdjbkdjjkdajksdjka" * 50
    compressed = snappy.compress(data, 2)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
