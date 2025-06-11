import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.snappy_sandbox import SnappyWasm

def main():
    snappy = SnappyWasm()

    data = b"hello world " * 10
    print("Original Length:   ", len(data))

    compressed = snappy.compress(data)
    print("Compressed Length: ", len(compressed))

    recovered_length = snappy.get_uncompressed_length(compressed)
    print("Recovered Length:  ", recovered_length)

    if recovered_length == len(data):
        print("get_uncompressed_length matches original length")
    else:
        print("Mismatch in recovered length!")

if __name__ == "__main__":
    main()
