import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm

def test_raw_compress_from_iovec():
    wasm_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'snappywasm/wasm/snappy.wasm'))
    snappy = SnappyWasm(wasm_path)

    data = [b"hello", b" ", b"snappy", b" ", b"iovec"]
    original = b"".join(data)
    print(f"[INFO] Original data: {original!r} ({len(original)} bytes)")

    compressed = snappy.raw_compress_from_iovec(data)
    print(f"[INFO] Compressed length: {len(compressed)} bytes")

    uncompressed = snappy.uncompress(compressed)
    print(f"[INFO] Uncompressed matches original: {uncompressed == original}")
    assert uncompressed == original
    print("[PASS] RawCompressFromIOVec round-trip OK.")

if __name__ == "__main__":
    test_raw_compress_from_iovec()