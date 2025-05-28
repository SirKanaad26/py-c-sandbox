
from snappywasm.core import SnappyWasmDirect

def main():
    snappy = SnappyWasmDirect(wasm_path="snappy.wasm")
    data = b"hello world " * 10
    compressed = snappy.compress(data)
    print("Compressed Length:", len(compressed))
    print("Original Length:", len(data))

if __name__ == "__main__":
    main()
