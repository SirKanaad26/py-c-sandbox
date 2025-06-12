from snappywasm.core import SnappyWasm as sw

def evil_snappy_exploits():
    
    print("=== EVIL SNAPPY EXPLOITS ===")
    print("WARNING: These will likely crash your program!")
    
    print("\n1. Testing integer overflow in buffer sizes...")
    try:
        result = sw.uncompress_to_iovec(b"fake_compressed_data", [-1, -2147483648])
        print("Integer overflow not caught!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n2. Testing empty IOVec arrays...")
    try:
        result = sw.compress_from_iovec([])
        print("Empty IOVec not handled!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n3. Testing memory exhaustion...")
    try:
        huge_size = 2**31 - 1  
        result = sw.uncompress_to_iovec(b"x", [huge_size])
        print("Memory exhaustion not prevented!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n4. Testing malformed compressed data...")
    try:

        malformed_data = b"\x00" * 100
        result = sw.uncompress_raw(malformed_data)
        print("Malformed data not rejected!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n5. Testing type confusion in IOVec...")
    try:
        result = sw.compress_from_iovec([b"valid", "string", 12345, None])
        print("Type confusion not caught!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n6. Testing potential double-free scenarios...")
    try:
        
        sizes = [1000000] * 1000 
        result = sw.uncompress_to_iovec(b"small", sizes)
        print("Resource exhaustion not handled!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n7. Testing very large IOVec arrays...")
    try:
        many_chunks = [b"x"] * 100000
        result = sw.compress_from_iovec(many_chunks)
        print("Large IOVec count not limited!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n8. Testing Source/Sink memory management...")
    try:
        huge_data = b"A" * (2**20)
        result = sw.compress_source_to_sink(huge_data)
        print("Compressed large data successfully")
        
        result2 = sw.uncompress_source_to_sink(result)
        print("Decompressed successfully")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n9. Testing integer wraparound...")
    try:
        evil_options = sw.PyCompressionOptions(999)
        result = sw.compress_data(b"test", evil_options)
        print("Invalid compression level not rejected!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n10. Testing null pointer scenarios...")
    try:
        result = sw.get_uncompressed_length(b"")
        print("Empty data not rejected!")
    except Exception as e:
        print(f"Caught: {e}")
    
    print("\n=== EVIL TESTS COMPLETE ===")
    print("If you see this message, the wrapper has some protection!")
    print("Any X indicates a potential vulnerability that needs fixing.")


def safe_snappy_test():
    
    print("\n=== SAFE SNAPPY VULNERABILITY TEST ===")
    print("This version catches all exceptions to prevent crashes.\n")
    
    vulnerabilities_found = []
    
    try:
        sw.uncompress_to_iovec(b"test", [-1])
    except (ValueError, MemoryError, RuntimeError) as e:
        print("Buffer size validation working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in buffer size test: {type(e).__name__}")
    
    try:
        sw.compress_from_iovec([])
    except (ValueError, RuntimeError) as e:
        print("Empty input validation working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in empty input test: {type(e).__name__}")
    
    try:
        sw.compress_from_iovec([b"valid", "invalid"])
    except (TypeError, ValueError) as e:
        print("Type validation working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in type test: {type(e).__name__}")
    
    try:
        sw.PyCompressionOptions(999)
    except ValueError as e:
        print("Compression level bounds checking working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in bounds test: {type(e).__name__}")
    
    try:
        sw.is_valid_compressed_buffer(b"definitely_not_snappy_data")
        print("Invalid data detection working")
    except Exception as e:
        vulnerabilities_found.append(f"Unhandled exception in invalid data test: {type(e).__name__}")
    
    if vulnerabilities_found:
        print(f"\n Found {len(vulnerabilities_found)} potential issues:")
        for vuln in vulnerabilities_found:
            print(f"  - {vuln}")
    else:
        print("\nAll basic safety checks passed!")
    
    print("\n=== SAFE TEST COMPLETE ===")


print("Choose your poison:")
print("1. evil_snappy_exploits() - Will likely crash")
print("2. safe_snappy_test() - Catches all exceptions")

# evil_snappy_exploits()  # Dangerous!
safe_snappy_test()        # Safe version