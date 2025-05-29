import sys
import os

# Add the parent directory to the Python path so we can import snappywasm
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from the snappywasm directory
from snappywasm.core import SnappyWasm

def main():
    # Update the path to point to your WASM file
    # Based on your directory structure, the WASM file might be in the current directory
    wasm_path = "snappy.wasm"  # or whatever your WASM file is named
    
    # Check if WASM file exists in current directory
    if not os.path.exists(wasm_path):
        print(f"WASM file not found: {wasm_path}")
        print("Available files in current directory:")
        for f in sorted(os.listdir(".")):
            if f.endswith(('.wasm', '.py', '.sh')):
                print(f"  {f}")
        
        # Try common names
        for possible_name in ["snappy.wasm", "snappy_direct.wasm", "snappy_source.wasm"]:
            if os.path.exists(possible_name):
                wasm_path = possible_name
                print(f"Found WASM file: {wasm_path}")
                break
        else:
            print("No WASM file found. Please build it first with ./build_wasm.sh")
            return
    
    try:
        snappy = SnappyWasm(wasm_path)
        print(f"Successfully loaded WASM module: {wasm_path}")
        print(f"WASM Version: {snappy.get_version()}")
    except Exception as e:
        print(f"Failed to load WASM module: {e}")
        return
    
    # Original data
    data = b"hello world " * 10
    print(f"\nOriginal data: {data}")
    print(f"Original length: {len(data)} bytes")
    
    # Compress the data
    try:
        compressed = snappy.compress(data)
        print(f"Compressed length: {len(compressed)} bytes")
        print(f"Compression ratio: {(1 - len(compressed)/len(data))*100:.1f}%")
    except Exception as e:
        print(f"Compression failed: {e}")
        return
    
    # Define how to split the decompressed data into multiple buffers
    # Split into 3 buffers: first 40 bytes, next 40 bytes, remaining bytes
    buffer_sizes = [40, 40, len(data) - 80]
    print(f"\nTarget buffer sizes: {buffer_sizes}")
    print(f"Total buffer size: {sum(buffer_sizes)} bytes")
    
    # Test RawUncompressToIOVec (char* version)
    print("\n--- RawUncompressToIOVec (char* version) ---")
    try:
        iovec_buffers = snappy.raw_uncompress_to_iovec(compressed, buffer_sizes)
        print(f"Successfully decompressed into {len(iovec_buffers)} buffers")
        
        for i, buffer in enumerate(iovec_buffers):
            print(f"Buffer {i}: {len(buffer)} bytes - {buffer}")
        
        # Verify integrity by reconstructing original data
        reconstructed = b"".join(iovec_buffers)
        integrity_check = data == reconstructed
        print(f"Data integrity: {'PASS' if integrity_check else 'FAIL'}")
        
    except AttributeError as e:
        print(f"RawUncompressToIOVec method not found: {e}")
        print("This means the SnappyWasm class doesn't have the raw_uncompress_to_iovec method yet.")
        print("You may need to add the extended methods to your SnappyWasm class.")
    except RuntimeError as e:
        print(f"RawUncompressToIOVec failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    # Test other RawUncompressToIOVec variants if available
    print("\n--- Testing other IOVec variants ---")
    
    try:
        # Test RawUncompressToIOVecFromSource (Source* version)
        source_buffers = snappy.raw_uncompress_to_iovec_from_source(compressed, buffer_sizes)
        print(f"RawUncompressToIOVecFromSource: {len(source_buffers)} buffers")
        
        source_reconstructed = b"".join(source_buffers)
        source_check = data == source_reconstructed
        print(f"Source version integrity: {'PASS' if source_check else 'FAIL'}")
        
    except AttributeError:
        print("raw_uncompress_to_iovec_from_source method not available")
    except Exception as e:
        print(f"Source version failed: {e}")
    
    try:
        # Test RawUncompressToBuffers (simplified version)
        simple_buffers = snappy.raw_uncompress_to_buffers(compressed, buffer_sizes)
        print(f"RawUncompressToBuffers: {len(simple_buffers)} buffers")
        
        simple_reconstructed = b"".join(simple_buffers)
        simple_check = data == simple_reconstructed
        print(f"Simplified version integrity: {'PASS' if simple_check else 'FAIL'}")
        
    except AttributeError:
        print("raw_uncompress_to_buffers method not available")
    except Exception as e:
        print(f"Simplified version failed: {e}")

if __name__ == "__main__":
    main()