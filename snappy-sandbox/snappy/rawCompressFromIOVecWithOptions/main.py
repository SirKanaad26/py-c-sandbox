import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'snappywasm')))
from snappywasm.core import SnappyWasm

def main():
    print("======= SnappyWasm RawCompressFromIOVecWithOptions Tests =======")

    wasm_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'snappywasm/wasm/snappy.wasm'))
    print(f"[SETUP] Using WASM file: {wasm_path}")
    
    sn = SnappyWasm(wasm_path)
    print("[SETUP] SnappyWasm object created.")
    print(f"[INFO] Compression level range: {sn.get_min_compression_level()} to {sn.get_max_compression_level()}")

    # Test 1: Valid compression level
    print("\n[Test] RawCompressFromIOVecWithOptions (valid option)")
    buffers = [b"A" * 100, b"B" * 200]
    original = b"".join(buffers)
    level = sn.get_min_compression_level()
    print(f"[INFO] Using compression level: {level}")

    comp = sn.raw_compress_from_iovec_with_options(buffers, options=level)
    print(f"[INFO] Compressed output length: {len(comp)} bytes")

    outbuf = bytearray(len(original))
    ok = sn.raw_uncompress(comp, outbuf)
    print(f"[INFO] Decompression success: {ok}")
    print(f"[INFO] Uncompressed matches original: {bytes(outbuf) == original}")

    assert ok, "Decompression failed"
    assert bytes(outbuf) == original, "Decompressed output does not match original"
    print("[PASS] RawCompressFromIOVecWithOptions round-trip OK.")

    # Test 2: Invalid compression levels
    print("\n[Test] RawCompressFromIOVecWithOptions (invalid options)")
    buffers = [b"x" * 10]
    
    try:
        sn.raw_compress_from_iovec_with_options(buffers, options=sn.get_max_compression_level() + 1)
        print("[FAIL] Expected RuntimeError for too high compression level")
    except RuntimeError:
        print("[PASS] Correctly raised RuntimeError for high option")
    except Exception as e:
        print(f"[FAIL] Raised unexpected exception: {e}")
    
    try:
        sn.raw_compress_from_iovec_with_options(buffers, options=-100)
        print("[FAIL] Expected RuntimeError for too low compression level")
    except RuntimeError:
        print("[PASS] Correctly raised RuntimeError for low option")
    except Exception as e:
        print(f"[FAIL] Raised unexpected exception: {e}")

if __name__ == "__main__":
    main()





