import os
import struct
from wasmtime import Store, Module, Instance, Func
from .utils import create_wasm_imports
import ctypes
from typing import List, Union

class SnappyWasm:
    def __init__(self, wasm_path="snappywasm/wasm/snappy.wasm"):
        if not os.path.exists(wasm_path):
            raise FileNotFoundError(f"WASM file not found: {wasm_path}")

        self.store = Store()

        with open(wasm_path, 'rb') as f:
            wasm_bytes = f.read()

        module = Module(self.store.engine, wasm_bytes)
        imports_needed = module.imports

        if len(imports_needed) > 0:
            imports = create_wasm_imports(self.store)
            import_list = []
            for imp in imports_needed:
                if imp.module in imports and imp.name in imports[imp.module]:
                    import_list.append(imports[imp.module][imp.name])
                else:
                    dummy = Func(self.store, imp.type, lambda *args: 0 if len(imp.type.results) > 0 else None)
                    import_list.append(dummy)
            self.instance = Instance(self.store, module, import_list)
        else:
            self.instance = Instance(self.store, module, [])

        self.exports = self.instance.exports(self.store)
        self.memory = self.exports.get("memory", None)

    def max_compressed_length(self, source_length: int) -> int:
        func = self.exports.get("MaxCompressedLength")
        if not func:
            raise RuntimeError("MaxCompressedLength not found")
        return func(self.store, source_length)
    
    def get_uncompressed_length(self, compressed_data: bytes) -> int:
        """Get the uncompressed length from compressed data"""
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("GetUncompressedLength")
        if not func:
            raise RuntimeError("GetUncompressedLength not found")

        compressed_len = len(compressed_data)
        
        compressed_offset = 0
        result_offset = compressed_len + 1024  # offset for storing the result

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call get uncompressed length function
        success = func(self.store, compressed_offset, compressed_len, result_offset)
        
        if not success:
            raise RuntimeError("Failed to get uncompressed length")

        # Read the result (size_t, typically 8 bytes on 64-bit, 4 on 32-bit)
        # For WASM, we'll assume 4 bytes (32-bit)
        result_bytes = bytearray(4)
        result_array = (ctypes.c_ubyte * 4).from_buffer(result_bytes)
        ctypes.memmove(result_array, raw_addr + result_offset, 4)
        
        # Convert bytes back to integer (little-endian)
        uncompressed_length = struct.unpack('<I', result_bytes)[0]
        return uncompressed_length

    def compress(self, input_data: bytes) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("CompressFromPtr")
        if not func:
            raise RuntimeError("CompressFromPtr not found")

        max_out_len = self.max_compressed_length(len(input_data))
        input_len = len(input_data)

        # Define offset to write input and output
        input_offset = 0
        output_offset = input_len + 1024  # leave a gap to prevent overwrite

        # Convert input to byte array
        src_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy input data into WASM memory
        ctypes.memmove(raw_addr + input_offset, src_array, input_len)

        # Call compress function
        compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len)
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")

        # Allocate output buffer
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)

        # Copy back compressed result
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)

        return bytes(result)

    def compress_from_iovec(self, data_buffers: List[Union[bytes, bytearray]], compression_level=-1) -> bytes:
        """
        Compress data from multiple buffers using Snappy's CompressFromIOVec functionality.
        
        Args:
            data_buffers: List of byte buffers to compress
            
        Returns:
            Compressed data as bytes
            
        Raises:
            RuntimeError: If compression fails or WASM function not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        if compression_level == -1:
            func = self.exports.get("CompressFromIOVec")
        else:
            func = self.exports.get(f"CompressFromIOVecWithOptions")

        if not func:
            raise RuntimeError("CompressFromIOVec not found")

        if not data_buffers:
            return b''

        # Calculate total input length and max compressed length
        total_input_len = sum(len(buf) for buf in data_buffers)
        max_out_len = self.max_compressed_length(total_input_len)
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Memory layout:
        # 1. iovec structures (each 8 bytes: 4 bytes ptr + 4 bytes len)
        # 2. Data buffers
        # 3. Output buffer
        
        iovec_count = len(data_buffers)
        iovec_size = 8  # sizeof(struct iovec) in WASM (ptr + len)
        iovec_array_size = iovec_count * iovec_size
        
        # Calculate offsets
        iovec_offset = 0
        data_start_offset = iovec_array_size + 64  # padding for alignment
        output_offset = data_start_offset + total_input_len + 1024  # gap to prevent overwrite
        
        # Build iovec array and copy data
        current_data_offset = data_start_offset
        
        for i, buffer in enumerate(data_buffers):
            buffer_len = len(buffer)
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            
            # Write iovec structure (ptr, len) - both as 32-bit values in WASM
            ptr_bytes = struct.pack('<I', current_data_offset)  # pointer (32-bit)
            len_bytes = struct.pack('<I', buffer_len)           # length (32-bit)
            
            # Copy iovec entry to WASM memory
            ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
            len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
            
            ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
            ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
            
            # Copy buffer data to WASM memory
            if buffer_len > 0:
                buffer_array = (ctypes.c_ubyte * buffer_len).from_buffer_copy(buffer)
                ctypes.memmove(raw_addr + current_data_offset, buffer_array, buffer_len)
            
            current_data_offset += buffer_len

        # Call CompressFromIOVec function
        # Function signature: size_t CompressFromIOVec(const struct iovec* iov, size_t iov_cnt, char* output, size_t output_len)
        if compression_level == -1:
            compressed_len = func(self.store, iovec_offset, iovec_count, output_offset, max_out_len)
        else:
            compressed_len = func(self.store, iovec_offset, iovec_count, output_offset, max_out_len, compression_level)
        
        if compressed_len <= 0:
            raise RuntimeError("IOVec compression failed")

        # Read compressed result
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)

        return bytes(result)

    def uncompress(self, compressed_data: bytes) -> bytes:
        """Uncompress data using Snappy WASM"""
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressFromPtr")
        if not func:
            raise RuntimeError("UncompressFromPtr not found")

        # First, get the expected uncompressed length
        try:
            uncompressed_length = self.get_uncompressed_length(compressed_data)
        except RuntimeError:
            # Fallback: estimate a reasonable buffer size
            uncompressed_length = len(compressed_data) * 4  # Conservative estimate

        compressed_len = len(compressed_data)

        # Define offsets
        compressed_offset = 0
        output_offset = compressed_len + 1024  # leave a gap to prevent overwrite

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call uncompress function
        actual_uncompressed_len = func(self.store, compressed_offset, compressed_len, output_offset, uncompressed_length)
        
        if actual_uncompressed_len <= 0:
            raise RuntimeError("Decompression failed")

        # Allocate output buffer
        result = bytearray(actual_uncompressed_len)
        result_array = (ctypes.c_ubyte * actual_uncompressed_len).from_buffer(result)

        # Copy back uncompressed result
        ctypes.memmove(result_array, raw_addr + output_offset, actual_uncompressed_len)

        return bytes(result)

    def is_valid_compressed_buffer(self, compressed_data: bytes) -> bool:
        """Validate if the data is properly compressed with Snappy"""
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("IsValidCompressedBuffer")
        if not func:
            raise RuntimeError("IsValidCompressedBuffer not found")

        compressed_len = len(compressed_data)
        
        # Define offset
        compressed_offset = 0

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call validation function (returns 1 for valid, 0 for invalid in WASM)
        is_valid = func(self.store, compressed_offset, compressed_len)
        
        return bool(is_valid)

    def get_min_compression_level(self) -> int:
        func = self.exports.get("GetMinCompressionLevel")
        if not func:
            return 1  # Default fallback
        return func(self.store)

    def get_max_compression_level(self) -> int:
        func = self.exports.get("GetMaxCompressionLevel")
        if not func:
            return 2  # Default fallback
        return func(self.store)

    def get_default_compression_level(self) -> int:
        func = self.exports.get("GetDefaultCompressionLevel")
        if not func:
            return 1  # Default fallback
        return func(self.store)

    def get_compression_info(self) -> dict:
        return {
            "min_level": self.get_min_compression_level(),
            "max_level": self.get_max_compression_level(),
            "default_level": self.get_default_compression_level(),
            "supported_levels": list(range(self.get_min_compression_level(), self.get_max_compression_level() + 1))
        }

    def get_version(self) -> int:
        func = self.exports.get("GetVersion")
        if not func:
            return 0
        return func(self.store)

if __name__ == "__main__":
    snappy = SnappyWasm("wasm/snappy_direct.wasm")
    
    print(f"Snappy WASM Version: {snappy.get_version()}")
    
    compression_info = snappy.get_compression_info()
    print(f"Compression Info: {compression_info}")
    
    original_data = b"Hello, this is a test string for Snappy compression and decompression! " * 10
    print(f"Original: {original_data[:50]}...")
    print(f"Original length: {len(original_data)} bytes")
    
    # Test regular compression
    print(f"\n--- Testing Regular Compression ---")
    compressed = snappy.compress(original_data)
    print(f"Compressed length: {len(compressed)} bytes")
    print(f"Compression ratio: {(1 - len(compressed)/len(original_data))*100:.1f}%")
    
    uncompressed = snappy.uncompress(compressed)
    integrity_check = original_data == uncompressed
    print(f"Data integrity check: {'PASS' if integrity_check else 'FAIL'}")
    
    # Test IOVec compression
    print(f"\n--- Testing IOVec Compression ---")
    
    # Split the data into multiple buffers to test IOVec functionality
    data_buffers = [
        b"Hello, this is a test string for Snappy compression",
        b" and decompression! ",
        original_data[71:200],  # middle chunk
        original_data[200:]     # remaining data
    ]
    
    print(f"Number of buffers: {len(data_buffers)}")
    print(f"Buffer sizes: {[len(buf) for buf in data_buffers]}")
    print(f"Total size: {sum(len(buf) for buf in data_buffers)} bytes")
    
    try:
        compressed_iovec = snappy.compress_from_iovec(data_buffers)
        print(f"IOVec compressed length: {len(compressed_iovec)} bytes")
        print(f"IOVec compression ratio: {(1 - len(compressed_iovec)/sum(len(buf) for buf in data_buffers))*100:.1f}%")
        
        is_valid = snappy.is_valid_compressed_buffer(compressed_iovec)
        print(f"IOVec compressed data is valid: {is_valid}")
        
        uncompressed_iovec = snappy.uncompress(compressed_iovec)
        reconstructed_data = b"".join(data_buffers)
        iovec_integrity_check = reconstructed_data == uncompressed_iovec
        print(f"IOVec data integrity check: {'PASS' if iovec_integrity_check else 'FAIL'}")
        
        # Compare with regular compression
        regular_compressed = snappy.compress(reconstructed_data)
        print(f"IOVec vs Regular size difference: {len(compressed_iovec) - len(regular_compressed)} bytes")
        
    except RuntimeError as e:
        print(f"IOVec compression test failed: {e}")
        print("Note: This may be expected if the WASM module doesn't include CompressFromIOVec")
    
    # Test edge cases
    print(f"\n--- Testing Edge Cases ---")
    
    # Empty buffers
    try:
        empty_result = snappy.compress_from_iovec([])
        print(f"Empty buffer list result: {len(empty_result)} bytes")
    except RuntimeError as e:
        print(f"Empty buffer list failed: {e}")
    
    # Single buffer (should behave like regular compression)
    try:
        single_buffer_result = snappy.compress_from_iovec([original_data])
        single_uncompressed = snappy.uncompress(single_buffer_result)
        single_check = original_data == single_uncompressed
        print(f"Single buffer IOVec integrity: {'PASS' if single_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Single buffer IOVec failed: {e}")
    
    # Mixed buffer types
    try:
        mixed_buffers = [
            b"bytes buffer",
            bytearray(b"bytearray buffer"),
            b"another bytes buffer"
        ]
        mixed_result = snappy.compress_from_iovec(mixed_buffers)
        mixed_uncompressed = snappy.uncompress(mixed_result)
        mixed_expected = b"".join(mixed_buffers)
        mixed_check = mixed_expected == mixed_uncompressed
        print(f"Mixed buffer types integrity: {'PASS' if mixed_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Mixed buffer types failed: {e}")