import os
import struct
from wasmtime import Store, Module, Instance, Func
from utils import create_wasm_imports
import ctypes

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
        
        # Define offsets
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

    def compress(self, input_data: bytes, compression_level: int = None) -> bytes:
        """Compress data using Snappy WASM
        
        Args:
            input_data: Data to compress
            compression_level: Optional compression level (1-2). If None, uses default level.
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        # Choose function based on whether compression level is specified
        if compression_level is not None:
            func = self.exports.get("CompressWithOptionsFromPtr")
            if not func:
                raise RuntimeError("CompressWithOptionsFromPtr not found")
        else:
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
        if compression_level is not None:
            compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len, compression_level)
        else:
            compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len)
            
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")

        # Allocate output buffer
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)

        # Copy back compressed result
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
        """Get the minimum supported compression level"""
        func = self.exports.get("GetMinCompressionLevel")
        if not func:
            return 1  # Default fallback
        return func(self.store)

    def get_max_compression_level(self) -> int:
        """Get the maximum supported compression level"""
        func = self.exports.get("GetMaxCompressionLevel")
        if not func:
            return 2  # Default fallback
        return func(self.store)

    def get_default_compression_level(self) -> int:
        """Get the default compression level"""
        func = self.exports.get("GetDefaultCompressionLevel")
        if not func:
            return 1  # Default fallback
        return func(self.store)

    def get_compression_info(self) -> dict:
        """Get information about available compression levels"""
        return {
            "min_level": self.get_min_compression_level(),
            "max_level": self.get_max_compression_level(),
            "default_level": self.get_default_compression_level(),
            "supported_levels": list(range(self.get_min_compression_level(), self.get_max_compression_level() + 1))
        }

    def compress_from_buffers(self, buffers: list, compression_level: int = None) -> bytes:
        """Compress data from multiple separate buffers as if they were one continuous stream
        
        Args:
            buffers: List of bytes objects to compress
            compression_level: Optional compression level (1-2). If None, uses default level.
            
        Returns:
            Compressed data as bytes
        """
        if not self.memory:
            raise RuntimeError("Memory not available")
        
        # Choose function based on whether compression level is specified
        if compression_level is not None:
            func = self.exports.get("CompressFromBuffersWithOptions")
            if not func:
                raise RuntimeError("CompressFromBuffersWithOptions not found")
        else:
            func = self.exports.get("CompressFromBuffers")
            if not func:
                raise RuntimeError("CompressFromBuffers not found")
        
        # Calculate total length and create flattened buffer
        total_length = sum(len(buf) for buf in buffers)
        buffer_count = len(buffers)
        
        if buffer_count == 0:
            # Handle empty buffer list
            return self.compress(b"", compression_level)
        
        # Estimate max compressed length
        max_compressed_len = self.max_compressed_length(total_length)
        
        # Create flattened buffer and lengths array
        flattened_buffer = bytearray(total_length)
        lengths = []
        offset = 0
        
        for buf in buffers:
            buf_len = len(buf)
            flattened_buffer[offset:offset + buf_len] = buf
            lengths.append(buf_len)
            offset += buf_len
        
        # Define memory offsets
        buffer_offset = 0
        lengths_offset = total_length + 1024
        output_offset = lengths_offset + (buffer_count * 8) + 1024  # 8 bytes per size_t in WASM
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        
        # Copy flattened buffer to WASM memory
        if total_length > 0:
            buffer_array = (ctypes.c_ubyte * total_length).from_buffer(flattened_buffer)
            ctypes.memmove(raw_addr + buffer_offset, buffer_array, total_length)
        
        # Copy lengths array to WASM memory (as 32-bit integers)
        lengths_bytes = bytearray()
        for length in lengths:
            lengths_bytes.extend(struct.pack('<I', length))  # Little-endian 32-bit unsigned int
        
        lengths_array = (ctypes.c_ubyte * len(lengths_bytes)).from_buffer(lengths_bytes)
        ctypes.memmove(raw_addr + lengths_offset, lengths_array, len(lengths_bytes))
        
        # Call compress function
        if compression_level is not None:
            compressed_len = func(self.store, buffer_offset, lengths_offset, buffer_count, 
                                output_offset, max_compressed_len, compression_level)
        else:
            compressed_len = func(self.store, buffer_offset, lengths_offset, buffer_count, 
                                output_offset, max_compressed_len)
        
        if compressed_len <= 0:
            raise RuntimeError("Multi-buffer compression failed")
        
        # Read compressed result
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)
        
        return bytes(result)
    
    def compress_from_iovec(self, iovec_data: list, compression_level: int = None) -> bytes:
        """Compress data using iovec structures (more advanced scatter-gather)
        
        Args:
            iovec_data: List of (offset, length) tuples representing iovec structures
            compression_level: Optional compression level (1-2). If None, uses default level.
            
        Returns:
            Compressed data as bytes
            
        Note: This is for advanced users who want direct iovec control.
        Most users should use compress_from_buffers() instead.
        """
        if not self.memory:
            raise RuntimeError("Memory not available")
        
        # Choose function based on whether compression level is specified
        if compression_level is not None:
            func = self.exports.get("CompressFromIOVecWithOptions")
            if not func:
                raise RuntimeError("CompressFromIOVecWithOptions not found")
        else:
            func = self.exports.get("CompressFromIOVec")
            if not func:
                raise RuntimeError("CompressFromIOVec not found")
        
        iov_cnt = len(iovec_data)
        
        if iov_cnt == 0:
            # Handle empty iovec list
            return self.compress(b"", compression_level)
        
        # Calculate total data size for compression estimation
        total_size = sum(length for _, length in iovec_data)
        max_compressed_len = self.max_compressed_length(total_size)
        
        # Create iovec structures in WASM format (8 bytes each: 4 bytes offset + 4 bytes length)
        iov_bytes = bytearray()
        for offset, length in iovec_data:
            iov_bytes.extend(struct.pack('<II', offset, length))  # Little-endian 32-bit unsigned ints
        
        # Define memory offsets
        iov_offset = 0
        output_offset = len(iov_bytes) + 1024
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        
        # Copy iovec data to WASM memory
        iov_array = (ctypes.c_ubyte * len(iov_bytes)).from_buffer(iov_bytes)
        ctypes.memmove(raw_addr + iov_offset, iov_array, len(iov_bytes))
        
        # Call compress function
        if compression_level is not None:
            compressed_len = func(self.store, iov_offset, iov_cnt, output_offset, 
                                max_compressed_len, compression_level)
        else:
            compressed_len = func(self.store, iov_offset, iov_cnt, output_offset, max_compressed_len)
        
        if compressed_len <= 0:
            raise RuntimeError("IOVec compression failed")
        
        # Read compressed result
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)
        
        return bytes(result)

    def get_version(self) -> int:
        """Get the version of the WASM module"""
        func = self.exports.get("GetVersion")
        if not func:
            return 0
        return func(self.store)

# Example usage:
if __name__ == "__main__":
    # Initialize the WASM module
    snappy = SnappyWasm("wasm/snappy.wasm")
    
    print(f"Snappy WASM Version: {snappy.get_version()}")
    
    # Get compression level information
    compression_info = snappy.get_compression_info()
    print(f"Compression Info: {compression_info}")
    
    # Test data
    original_data = b"Hello, this is a test string for Snappy compression and decompression! " * 10
    print(f"Original: {original_data[:50]}...")
    print(f"Original length: {len(original_data)} bytes")
    
    # Test different compression levels
    for level in compression_info["supported_levels"]:
        print(f"\n--- Testing Compression Level {level} ---")
        
        # Compress with specific level
        compressed = snappy.compress(original_data, compression_level=level)
        print(f"Compressed length (level {level}): {len(compressed)} bytes")
        print(f"Compression ratio (level {level}): {(1 - len(compressed)/len(original_data))*100:.1f}%")
        
        # Validate compressed data
        is_valid = snappy.is_valid_compressed_buffer(compressed)
        print(f"Compressed data is valid: {is_valid}")
        
        # Get uncompressed length
        expected_length = snappy.get_uncompressed_length(compressed)
        print(f"Expected uncompressed length: {expected_length} bytes")
        
        # Uncompress
        uncompressed = snappy.uncompress(compressed)
        print(f"Uncompressed length: {len(uncompressed)} bytes")
        
        # Verify integrity
        integrity_check = original_data == uncompressed
        print(f"Data integrity check: {'✅ PASS' if integrity_check else '❌ FAIL'}")
        
        if not integrity_check:
            print(f"Original:     {original_data[:100]}")
            print(f"Uncompressed: {uncompressed[:100]}")
    
    # Test multi-buffer compression
    print(f"\n--- Testing Multi-Buffer Compression ---")
    
    # Split the data into multiple buffers
    buffer1 = original_data[:30]
    buffer2 = original_data[30:60] 
    buffer3 = original_data[60:]
    buffers = [buffer1, buffer2, buffer3]
    
    print(f"Buffer 1: {len(buffer1)} bytes")
    print(f"Buffer 2: {len(buffer2)} bytes") 
    print(f"Buffer 3: {len(buffer3)} bytes")
    print(f"Total: {sum(len(b) for b in buffers)} bytes")
    
    # Test multi-buffer compression with different levels
    for level in compression_info["supported_levels"]:
        print(f"\n  Multi-buffer compression (level {level}):")
        
        # Compress from multiple buffers
        multi_compressed = snappy.compress_from_buffers(buffers, compression_level=level)
        print(f"  Multi-buffer compressed size: {len(multi_compressed)} bytes")
        
        # Compare with single buffer compression of the same data
        single_compressed = snappy.compress(original_data, compression_level=level)
        print(f"  Single buffer compressed size: {len(single_compressed)} bytes")
        
        # Verify they produce identical results
        if multi_compressed == single_compressed:
            print(f"  ✅ Multi-buffer matches single buffer compression")
        else:
            print(f"  ⚠️  Multi-buffer differs from single buffer")
        
        # Test decompression
        multi_uncompressed = snappy.uncompress(multi_compressed)
        multi_integrity = original_data == multi_uncompressed
        print(f"  Multi-buffer integrity: {'✅ PASS' if multi_integrity else '❌ FAIL'}")
    
    # Test default multi-buffer compression
    print(f"\n  Multi-buffer default compression:")
    multi_default = snappy.compress_from_buffers(buffers)
    single_default = snappy.compress(original_data)
    
    default_match = multi_default == single_default
    print(f"  Default multi-buffer matches single: {'✅ PASS' if default_match else '❌ FAIL'}")
    
    # Test with many small buffers
    print(f"\n--- Testing Many Small Buffers ---")
    small_buffers = [original_data[i:i+5] for i in range(0, len(original_data), 5)]
    print(f"Split into {len(small_buffers)} buffers of ~5 bytes each")
    
    many_compressed = snappy.compress_from_buffers(small_buffers)
    many_uncompressed = snappy.uncompress(many_compressed)
    many_integrity = original_data == many_uncompressed
    print(f"Many small buffers integrity: {'✅ PASS' if many_integrity else '❌ FAIL'}")
    print(f"Many buffers compressed size: {len(many_compressed)} bytes")
    
    # Test edge cases
    print(f"\n--- Testing Edge Cases ---")
    
    # Empty buffer list
    try:
        empty_result = snappy.compress_from_buffers([])
        print(f"Empty buffer list: {len(empty_result)} bytes")
    except Exception as e:
        print(f"Empty buffer list error: {e}")
    
    # Single buffer (should match regular compress)
    single_buf_result = snappy.compress_from_buffers([original_data])
    regular_result = snappy.compress(original_data)
    single_match = single_buf_result == regular_result
    print(f"Single buffer in list matches regular: {'✅ PASS' if single_match else '❌ FAIL'}")
    
    # Buffer with empty elements
    mixed_buffers = [b"Hello", b"", b"World", b"!", b""]
    mixed_compressed = snappy.compress_from_buffers(mixed_buffers)
    mixed_uncompressed = snappy.uncompress(mixed_compressed)
    expected_mixed = b"HelloWorld!"
    mixed_integrity = expected_mixed == mixed_uncompressed
    print(f"Mixed buffers (with empty): {'✅ PASS' if mixed_integrity else '❌ FAIL'}")
    print(f"Mixed result: {mixed_uncompressed}")