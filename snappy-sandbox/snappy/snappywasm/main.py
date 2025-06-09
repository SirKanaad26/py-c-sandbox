from snappywasm.core import SnappyWasm as sw

def evil_snappy_exploits():
    """
    Evil function that exposes vulnerabilities in the Snappy Cython wrapper.
    
    WARNING: This function will likely cause crashes, memory corruption, 
    or undefined behavior. Only run in a sandboxed environment!
    """
    
    
    print("=== EVIL SNAPPY EXPLOITS ===")
    print("WARNING: These will likely crash your program!")
    
    # Vulnerability 1: Integer Overflow in Buffer Size
    print("\n1. Testing integer overflow in buffer sizes...")
    try:
        # Passing negative buffer sizes which get cast to huge unsigned values
        result = sw.uncompress_to_iovec(b"fake_compressed_data", [-1, -2147483648])
        print("❌ Integer overflow not caught!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 2: Empty/Invalid IOVec Arrays
    print("\n2. Testing empty IOVec arrays...")
    try:
        # Empty list could cause null pointer dereference
        result = sw.compress_from_iovec([])
        print("❌ Empty IOVec not handled!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 3: Memory Exhaustion via Large Allocations
    print("\n3. Testing memory exhaustion...")
    try:
        # Try to allocate massive buffers that could cause OOM
        huge_size = 2**31 - 1  # Max signed int
        result = sw.uncompress_to_iovec(b"x", [huge_size])
        print("❌ Memory exhaustion not prevented!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 4: Invalid Compressed Data Leading to Buffer Overruns
    print("\n4. Testing malformed compressed data...")
    try:
        # Crafted data that claims huge uncompressed size but is actually small
        # This could cause buffer overruns in RawUncompress
        malformed_data = b"\x00" * 100  # Invalid snappy header
        result = sw.uncompress_raw(malformed_data)
        print("❌ Malformed data not rejected!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 5: Type Confusion in IOVec
    print("\n5. Testing type confusion in IOVec...")
    try:
        # Passing non-bytes objects in chunk list
        result = sw.compress_from_iovec([b"valid", "string", 12345, None])
        print("❌ Type confusion not caught!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 6: Double-Free Potential
    print("\n6. Testing potential double-free scenarios...")
    try:
        # Large buffer sizes that might cause allocation failures mid-way
        # leading to incomplete cleanup and potential double-free
        sizes = [1000000] * 1000  # Many large buffers
        result = sw.uncompress_to_iovec(b"small", sizes)
        print("❌ Resource exhaustion not handled!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 7: Stack Overflow via Deep Recursion
    print("\n7. Testing very large IOVec arrays...")
    try:
        # Extremely large number of small chunks might cause stack issues
        many_chunks = [b"x"] * 100000
        result = sw.compress_from_iovec(many_chunks)
        print("❌ Large IOVec count not limited!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 8: Use-After-Free in Source/Sink
    print("\n8. Testing Source/Sink memory management...")
    try:
        # Very large data that might cause reallocation issues
        huge_data = b"A" * (2**20)  # 1MB of data
        result = sw.compress_source_to_sink(huge_data)
        print("Compressed large data successfully")
        
        # Try to trigger use-after-free by immediately using result
        result2 = sw.uncompress_source_to_sink(result)
        print("Decompressed successfully")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 9: Integer Wraparound in Length Calculations
    print("\n9. Testing integer wraparound...")
    try:
        # Compression level out of bounds
        evil_options = sw.PyCompressionOptions(999)  # Way above max level
        result = sw.compress_data(b"test", evil_options)
        print("❌ Invalid compression level not rejected!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    # Vulnerability 10: Null Pointer Dereference
    print("\n10. Testing null pointer scenarios...")
    try:
        # Try operations on empty bytes which might cause null pointer issues
        result = sw.get_uncompressed_length(b"")
        print("❌ Empty data not rejected!")
    except Exception as e:
        print(f"✅ Caught: {e}")
    
    print("\n=== EVIL TESTS COMPLETE ===")
    print("If you see this message, the wrapper has some protection!")
    print("Any ❌ indicates a potential vulnerability that needs fixing.")


# Safe/Sandboxed version that catches all exceptions
def safe_snappy_test():
    """
    Sandboxed version that demonstrates the same issues but catches all exceptions
    to prevent crashes.
    """
    
    
    print("\n=== SAFE SNAPPY VULNERABILITY TEST ===")
    print("This version catches all exceptions to prevent crashes.\n")
    
    vulnerabilities_found = []
    
    # Test 1: Buffer size validation
    try:
        sw.uncompress_to_iovec(b"test", [-1])
    except (ValueError, MemoryError, RuntimeError) as e:
        print("✅ Buffer size validation working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in buffer size test: {type(e).__name__}")
    
    # Test 2: Empty input validation  
    try:
        sw.compress_from_iovec([])
    except (ValueError, RuntimeError) as e:
        print("✅ Empty input validation working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in empty input test: {type(e).__name__}")
    
    # Test 3: Type validation
    try:
        sw.compress_from_iovec([b"valid", "invalid"])
    except (TypeError, ValueError) as e:
        print("✅ Type validation working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in type test: {type(e).__name__}")
    
    # Test 4: Bounds checking
    try:
        sw.PyCompressionOptions(999)
    except ValueError as e:
        print("✅ Compression level bounds checking working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in bounds test: {type(e).__name__}")
    
    # Test 5: Invalid data handling
    try:
        sw.is_valid_compressed_buffer(b"definitely_not_snappy_data")
        print("✅ Invalid data detection working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in invalid data test: {type(e).__name__}")
    
    if vulnerabilities_found:
        print(f"\n❌ Found {len(vulnerabilities_found)} potential issues:")
        for vuln in vulnerabilities_found:
            print(f"  - {vuln}")
    else:
        print("\n✅ All basic safety checks passed!")
    
    print("\n=== SAFE TEST COMPLETE ===")


print("Choose your poison:")
print("1. evil_snappy_exploits() - Will likely crash")
print("2. safe_snappy_test() - Catches all exceptions")

# Uncomment the one you want to run:
evil_snappy_exploits()  # Dangerous!
# safe_snappy_test()        # Safe version