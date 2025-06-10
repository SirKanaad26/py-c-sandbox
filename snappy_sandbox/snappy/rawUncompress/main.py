import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snappywasm.core import SnappyWasm

def test_raw_uncompress():
    print("Testing Raw Uncompress Functionality\n")
    
    try:
        snappy = SnappyWasm()
        print("SnappyWasm initialized successfully\n")
    except Exception as e:
        print(f"Initialization failed: {e}")
        return False

    test_cases = [
        b"Hello, World!",
        b"This is a longer test string for Snappy compression testing. " * 2,
    ]
    all_ok = True

    for i, original in enumerate(test_cases, 1):
        print(f"--- Case {i} ---")
        print(f"Original ({len(original)} bytes): {original!r}")

        comp = snappy.compress(original)
        print(f"Compressed ({len(comp)} bytes): {comp!r}")

        buf = bytearray(len(original))
        ok = snappy.raw_uncompress(comp, buf)
        print(f"raw_uncompress returned: {ok}")
        print(f"Uncompressed ({len(buf)} bytes): {buf!r}\n")

        if not ok or bytes(buf) != original:
            print(" MISMATCH!\n")
            all_ok = False
        else:
            print(" Match!\n")

    return all_ok


def test_integration():
    print("Integration Test")
    snappy = SnappyWasm()
    original = b"Integration test for raw_uncompress."
    print(f"Original: {original!r}")

    comp = snappy.compress(original)
    print(f"Compressed: {comp!r}")

    buf = bytearray(len(original))
    ok = snappy.raw_uncompress(comp, buf)
    print(f"raw_uncompress returned: {ok}")
    print(f"Recovered: {buf!r}")

    if ok and bytes(buf) == original:
        print(" Integration succeeded\n")
        return True
    else:
        print("✗ Integration failed\n")
        return False


if __name__ == "__main__":
    a = test_raw_uncompress()
    b = test_integration()
    if a and b:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Tests failed.")
        sys.exit(1)
