#!/usr/bin/env python3
from snappywasm.core import SnappyWasm

def main():
    # Instantiate the Snappy WASM wrapper
    snappy = SnappyWasm()

    # Example data to compress
    data = b"hello world " * 10
    print("Original Length:   ", len(data))

    # Compress
    compressed = snappy.compress(data)
    print("Compressed Length: ", len(compressed))

    # Retrieve uncompressed length from the compressed blob
    recovered_length = snappy.get_uncompressed_length(compressed)
    print("Recovered Length:  ", recovered_length)

    # Verify round‑trip
    if recovered_length == len(data):
        print("get_uncompressed_length matches original length")
    else:
        print("Mismatch in recovered length!")

if __name__ == "__main__":
    main()
