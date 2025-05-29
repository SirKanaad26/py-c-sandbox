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

        # Choose function based on whether compression level is specified
        if compression_level is not None:
            print("here")
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

    def raw_uncompress(self, compressed_data: bytes) -> bytes:
        """
        Raw uncompress data using Snappy's RawUncompress functionality.
        This is a lower-level interface compared to uncompress().
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompress")
        if not func:
            raise RuntimeError("RawUncompress not found")

        # Get the expected uncompressed length
        uncompressed_length = self.get_uncompressed_length(compressed_data)
        compressed_len = len(compressed_data)

        # Define offsets
        compressed_offset = 0
        output_offset = compressed_len + 1024

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call raw uncompress function
        success = func(self.store, compressed_offset, compressed_len, output_offset)
        
        if not success:
            raise RuntimeError("Raw decompression failed")

        # Allocate output buffer
        result = bytearray(uncompressed_length)
        result_array = (ctypes.c_ubyte * uncompressed_length).from_buffer(result)

        # Copy back uncompressed result
        ctypes.memmove(result_array, raw_addr + output_offset, uncompressed_length)

        return bytes(result)

    def raw_uncompress_from_source(self, compressed_data: bytes) -> bytes:
        """
        Raw uncompress data using Snappy's RawUncompressFromSource functionality.
        This uses the Source* abstraction internally.
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressFromSource")
        if not func:
            raise RuntimeError("RawUncompressFromSource not found")

        # Get the expected uncompressed length
        uncompressed_length = self.get_uncompressed_length(compressed_data)
        compressed_len = len(compressed_data)

        # Define offsets
        compressed_offset = 0
        output_offset = compressed_len + 1024

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call raw uncompress from source function
        success = func(self.store, compressed_offset, compressed_len, output_offset)
        
        if not success:
            raise RuntimeError("Raw decompression from source failed")

        # Allocate output buffer
        result = bytearray(uncompressed_length)
        result_array = (ctypes.c_ubyte * uncompressed_length).from_buffer(result)

        # Copy back uncompressed result
        ctypes.memmove(result_array, raw_addr + output_offset, uncompressed_length)

        return bytes(result)

    def raw_uncompress(self, compressed_data: bytes, uncompressed_length: int) -> bytes:
        """
        Uncompress Snappy-compressed data using the Source* abstraction.
        This uses RawUncompressFromSource which internally creates a ByteArraySource.
        
        Args:
            compressed_data: The compressed data bytes
            uncompressed_length: The expected length of uncompressed data
            
        Returns:
            bytes: The uncompressed data
            
        Raises:
            RuntimeError: If decompression fails or memory is not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressFromSource")
        if not func:
            raise RuntimeError("RawUncompressFromSource not found")

        compressed_len = len(compressed_data)
        
        # Calculate memory offsets (ensure they don't overlap)
        compressed_offset = 0
        uncompressed_offset = compressed_len + 16  # Add some padding
        
        # Ensure we have enough memory
        total_memory_needed = uncompressed_offset + uncompressed_length
        if total_memory_needed > self.memory.data_size(self.store):
            raise RuntimeError(f"Not enough WASM memory. Need {total_memory_needed}, have {self.memory.data_size(self.store)}")

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call decompression function with Source* abstraction
        success = func(self.store, compressed_offset, compressed_len, uncompressed_offset)
        
        if not success:
            raise RuntimeError("Decompression failed")

        # Read the uncompressed data from WASM memory
        uncompressed_array = (ctypes.c_ubyte * uncompressed_length).from_address(raw_addr + uncompressed_offset)
        uncompressed_data = bytes(uncompressed_array)
        
        return uncompressed_data

    def raw_uncompress_to_iovec(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using Snappy's RawUncompressToIOVec functionality.
        This is scatter-gather decompression - the compressed data is decompressed directly into
        multiple non-contiguous output buffers.
        
        Args:
            compressed_data: Compressed data to decompress
            buffer_sizes: List of sizes for each output buffer
            
        Returns:
            List of bytes objects, one for each output buffer
            
        Raises:
            RuntimeError: If decompression fails or WASM function not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToIOVec")
        if not func:
            raise RuntimeError("RawUncompressToIOVec not found")

        if not buffer_sizes:
            return []

        # Validate that total buffer size matches expected uncompressed length
        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Memory layout:
        # 1. Compressed data
        # 2. iovec structures (each 8 bytes: 4 bytes ptr + 4 bytes len)
        # 3. Output buffers
        
        iovec_size = 8  # sizeof(struct iovec) in WASM
        iovec_array_size = buffer_count * iovec_size
        
        # Calculate offsets
        compressed_offset = 0
        iovec_offset = compressed_len + 64  # padding for alignment
        buffers_start_offset = iovec_offset + iovec_array_size + 64  # more padding
        
        # Copy compressed data to WASM memory
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
        
        # Build iovec array and allocate output buffers
        current_buffer_offset = buffers_start_offset
        
        for i, buffer_size in enumerate(buffer_sizes):
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            
            # Write iovec structure (ptr, len) - both as 32-bit values in WASM
            ptr_bytes = struct.pack('<I', current_buffer_offset)  # pointer (32-bit)
            len_bytes = struct.pack('<I', buffer_size)            # length (32-bit)
            
            # Copy iovec entry to WASM memory
            ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
            len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
            
            ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
            ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
            
            current_buffer_offset += buffer_size

        # Call RawUncompressToIOVec function
        # Function signature: bool RawUncompressToIOVec(const char* compressed, size_t compressed_length, const struct iovec* iov, size_t iov_cnt)
        success = func(self.store, compressed_offset, compressed_len, iovec_offset, buffer_count)
        
        if not success:
            raise RuntimeError("IOVec raw decompression failed")

        # Read results from each buffer
        results = []
        current_buffer_offset = buffers_start_offset
        
        for buffer_size in buffer_sizes:
            result = bytearray(buffer_size)
            result_array = (ctypes.c_ubyte * buffer_size).from_buffer(result)
            ctypes.memmove(result_array, raw_addr + current_buffer_offset, buffer_size)
            results.append(bytes(result))
            current_buffer_offset += buffer_size

        return results

    def raw_uncompress_to_iovec_from_source(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using Snappy's RawUncompressToIOVecFromSource functionality.
        This uses the Source* abstraction internally and provides scatter-gather decompression.
        
        Args:
            compressed_data: Compressed data to decompress
            buffer_sizes: List of sizes for each output buffer
            
        Returns:
            List of bytes objects, one for each output buffer
            
        Raises:
            RuntimeError: If decompression fails or WASM function not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToIOVecFromSource")
        if not func:
            raise RuntimeError("RawUncompressToIOVecFromSource not found")

        if not buffer_sizes:
            return []

        # Validate that total buffer size matches expected uncompressed length
        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Memory layout is the same as raw_uncompress_to_iovec
        iovec_size = 8
        iovec_array_size = buffer_count * iovec_size
        
        compressed_offset = 0
        iovec_offset = compressed_len + 64
        buffers_start_offset = iovec_offset + iovec_array_size + 64
        
        # Copy compressed data to WASM memory
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
        
        # Build iovec array
        current_buffer_offset = buffers_start_offset
        
        for i, buffer_size in enumerate(buffer_sizes):
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            
            ptr_bytes = struct.pack('<I', current_buffer_offset)
            len_bytes = struct.pack('<I', buffer_size)
            
            ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
            len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
            
            ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
            ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
            
            current_buffer_offset += buffer_size

        # Call RawUncompressToIOVecFromSource function
        # This internally creates a ByteArraySource and calls snappy::RawUncompressToIOVec(&source, iov, iov_cnt)
        success = func(self.store, compressed_offset, compressed_len, iovec_offset, buffer_count)
        
        if not success:
            raise RuntimeError("IOVec raw decompression from source failed")

        # Read results from each buffer
        results = []
        current_buffer_offset = buffers_start_offset
        
        for buffer_size in buffer_sizes:
            result = bytearray(buffer_size)
            result_array = (ctypes.c_ubyte * buffer_size).from_buffer(result)
            ctypes.memmove(result_array, raw_addr + current_buffer_offset, buffer_size)
            results.append(bytes(result))
            current_buffer_offset += buffer_size

        return results

    def raw_uncompress_to_buffers(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using the simplified RawUncompressToBuffers functionality.
        This is an easier-to-use version that doesn't require complex iovec handling.
        
        Args:
            compressed_data: Compressed data to decompress
            buffer_sizes: List of sizes for each output buffer
            
        Returns:
            List of bytes objects, one for each output buffer
            
        Raises:
            RuntimeError: If decompression fails or WASM function not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToBuffers")
        if not func:
            raise RuntimeError("RawUncompressToBuffers not found")

        if not buffer_sizes:
            return []

        # Validate that total buffer size matches expected uncompressed length
        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Memory layout:
        # 1. Compressed data
        # 2. Lengths array (size_t array)
        # 3. Contiguous output buffer (all buffers concatenated)
        
        lengths_array_size = buffer_count * 4  # sizeof(size_t) in WASM (32-bit)
        
        # Calculate offsets
        compressed_offset = 0
        lengths_array_offset = compressed_len + 64
        output_buffer_offset = lengths_array_offset + lengths_array_size + 64
        
        # Copy compressed data to WASM memory
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
        
        # Copy buffer sizes array to WASM memory
        for i, size in enumerate(buffer_sizes):
            size_bytes = struct.pack('<I', size)  # 32-bit size_t
            size_array = (ctypes.c_ubyte * 4).from_buffer_copy(size_bytes)
            ctypes.memmove(raw_addr + lengths_array_offset + (i * 4), size_array, 4)

        # Call RawUncompressToBuffers function
        # Function signature: bool RawUncompressToBuffers(const char* compressed, size_t compressed_length, 
        #                                                 char* buffer_ptr, const size_t* lengths_ptr, size_t buffer_count)
        success = func(self.store, compressed_offset, compressed_len, output_buffer_offset, lengths_array_offset, buffer_count)
        
        if not success:
            raise RuntimeError("Simplified raw decompression to buffers failed")

        # Read results from the contiguous output buffer
        results = []
        current_offset = 0
        
        for buffer_size in buffer_sizes:
            result = bytearray(buffer_size)
            result_array = (ctypes.c_ubyte * buffer_size).from_buffer(result)
            ctypes.memmove(result_array, raw_addr + output_buffer_offset + current_offset, buffer_size)
            results.append(bytes(result))
            current_offset += buffer_size

        return results

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

    def is_valid_compressed(self, compressed_data: bytes) -> bool:
        """
        Validate if the data is properly compressed with Snappy using the Source* abstraction.
        This uses IsValidCompressed which internally creates a ByteArraySource.
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("IsValidCompressed")
        if not func:
            raise RuntimeError("IsValidCompressed not found")

        compressed_len = len(compressed_data)
        compressed_offset = 0

        # Convert compressed data to byte array
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy compressed data into WASM memory
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        # Call validation function with Source* abstraction
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
    
    def raw_uncompress(self, compressed_data: bytes, uncompressed_buffer: bytearray) -> bool:
        if not self.memory:
            return False

        func = self.exports.get("RawUncompress")
        if not func:
            return False

        if not compressed_data or len(uncompressed_buffer) == 0:
            return False

        compressed_len = len(compressed_data)
        uncompressed_len = len(uncompressed_buffer)

        # Define offsets in WASM memory
        compressed_offset = 0
        output_offset = compressed_len + 1024  # leave gap to prevent overwrite

        try:
            # Convert compressed data to byte array
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

            # Access WASM memory
            mem_ptr = self.memory.data_ptr(self.store)
            raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

            # Copy compressed data into WASM memory
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

            # Call raw uncompress function
            # Function signature: bool RawUncompress(const char* compressed, size_t compressed_length, char* uncompressed)
            success = func(self.store, compressed_offset, compressed_len, output_offset)
            
            if not success:
                return False

            # Copy uncompressed data back to the provided buffer
            result_array = (ctypes.c_ubyte * uncompressed_len).from_buffer(uncompressed_buffer)
            ctypes.memmove(result_array, raw_addr + output_offset, uncompressed_len)

            return True
            
        except Exception:
            return False
        
    def raw_uncompress_to_iovec_from_source(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using Snappy's RawUncompressToIOVec functionality
        with Source* abstraction. This creates a ByteArraySource internally and performs scatter-gather 
        decompression directly into multiple non-contiguous output buffers.
        
        Args:
            compressed_data: Compressed data to decompress 
            buffer_sizes: List of sizes for each output buffer
            
        Returns:
            List of bytes objects, one for each output buffer
            
        Raises:
            RuntimeError: If decompression fails or WASM function not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToIOVecFromSource")
        if not func:
            raise RuntimeError("RawUncompressToIOVecFromSource not found")

        if not buffer_sizes:
            return []

        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        # Validate that total buffer size matches expected uncompressed length
        total_buffer_size = sum(buffer_sizes)
        try:
            expected_length = self.get_uncompressed_length(compressed_data)
            if total_buffer_size != expected_length:
                raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")
        except Exception:
            # If we can't get uncompressed length, we'll let the WASM function validate
            pass

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Memory layout:
        # 1. Compressed data
        # 2. iovec structures (each 8 bytes: 4 bytes ptr + 4 bytes len)  
        # 3. Output buffers
        
        iovec_size = 8  # sizeof(struct iovec) in WASM (32-bit: ptr + len)
        iovec_array_size = buffer_count * iovec_size
        
        # Calculate offsets with padding for alignment
        compressed_offset = 0
        iovec_offset = compressed_len + 64  # padding for alignment
        buffers_start_offset = iovec_offset + iovec_array_size + 64  # more padding
        
        try:
            # Copy compressed data to WASM memory
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
            
            # Build iovec array and allocate output buffers
            current_buffer_offset = buffers_start_offset
            
            for i, buffer_size in enumerate(buffer_sizes):
                if buffer_size <= 0:
                    raise RuntimeError(f"Invalid buffer size at index {i}: {buffer_size}")
                    
                iovec_entry_offset = iovec_offset + (i * iovec_size)
                
                # Write iovec structure (ptr, len) - both as 32-bit values in WASM
                ptr_bytes = struct.pack('<I', current_buffer_offset)  # pointer (32-bit)
                len_bytes = struct.pack('<I', buffer_size)            # length (32-bit)
                
                # Copy iovec entry to WASM memory
                ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
                len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
                
                ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
                ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
                
                current_buffer_offset += buffer_size

            # Call RawUncompressToIOVecFromSource function
            # Function signature: bool RawUncompressToIOVecFromSource(const char* compressed_data, size_t compressed_length, const void* iov_ptr, size_t iov_cnt)
            success = func(self.store, compressed_offset, compressed_len, iovec_offset, buffer_count)
            
            if not success:
                raise RuntimeError("IOVec raw decompression from source failed")

            # Read results from each buffer
            results = []
            current_buffer_offset = buffers_start_offset
            
            for buffer_size in buffer_sizes:
                result = bytearray(buffer_size)
                result_array = (ctypes.c_ubyte * buffer_size).from_buffer(result)
                ctypes.memmove(result_array, raw_addr + current_buffer_offset, buffer_size)
                results.append(bytes(result))
                current_buffer_offset += buffer_size

            return results
            
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"IOVec decompression from source failed: {str(e)}")


if __name__ == "__main__":
    snappy = SnappyWasm("snappy.wasm")
    
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
    
    # Test validation functions
    print(f"\n--- Testing Validation Functions ---")
    is_valid_buffer = snappy.is_valid_compressed_buffer(compressed)
    print(f"IsValidCompressedBuffer: {is_valid_buffer}")
    
    is_valid_source = snappy.is_valid_compressed(compressed)
    print(f"IsValidCompressed (Source*): {is_valid_source}")
    
    # Test with invalid data
    invalid_data = b"This is not compressed data"
    is_valid_invalid = snappy.is_valid_compressed_buffer(invalid_data)
    print(f"Invalid data validation: {is_valid_invalid}")
    
    # Test Raw decompression functions
    print(f"\n--- Testing Raw Decompression Functions ---")
    
    try:
        raw_uncompressed = snappy.raw_uncompress(compressed)
        raw_integrity_check = original_data == raw_uncompressed
        print(f"RawUncompress integrity: {'PASS' if raw_integrity_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"RawUncompress failed: {e}")
    
    try:
        raw_uncompressed_source = snappy.raw_uncompress_from_source(compressed)
        raw_source_integrity_check = original_data == raw_uncompressed_source
        print(f"RawUncompressFromSource integrity: {'PASS' if raw_source_integrity_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"RawUncompressFromSource failed: {e}")
    
    # Test Scatter-Gather decompression (RawUncompressToIOVec)
    print(f"\n--- Testing Scatter-Gather Decompression (IOVec) ---")
    
    # Define how to split the decompressed data into multiple buffers
    # For example, split into 3 buffers of different sizes
    total_len = len(original_data)
    buffer_sizes = [total_len // 3, total_len // 3, total_len - 2 * (total_len // 3)]
    print(f"Target buffer sizes: {buffer_sizes} (total: {sum(buffer_sizes)})")
    
    try:
        # Test RawUncompressToIOVec (char* version)
        iovec_buffers = snappy.raw_uncompress_to_iovec(compressed, buffer_sizes)
        print(f"RawUncompressToIOVec returned {len(iovec_buffers)} buffers")
        print(f"Buffer lengths: {[len(buf) for buf in iovec_buffers]}")
        
        # Reconstruct original data from buffers
        reconstructed_iovec = b"".join(iovec_buffers)
        iovec_integrity_check = original_data == reconstructed_iovec
        print(f"IOVec integrity: {'PASS' if iovec_integrity_check else 'FAIL'}")
        
        # Show first few bytes of each buffer
        for i, buf in enumerate(iovec_buffers):
            print(f"  Buffer {i}: {buf[:20]}...")
            
    except RuntimeError as e:
        print(f"RawUncompressToIOVec failed: {e}")
    
    try:
        # Test RawUncompressToIOVecFromSource (Source* version)
        iovec_source_buffers = snappy.raw_uncompress_to_iovec_from_source(compressed, buffer_sizes)
        print(f"RawUncompressToIOVecFromSource returned {len(iovec_source_buffers)} buffers")
        print(f"Buffer lengths: {[len(buf) for buf in iovec_source_buffers]}")
        
        # Reconstruct original data from buffers
        reconstructed_source_iovec = b"".join(iovec_source_buffers)
        source_iovec_integrity_check = original_data == reconstructed_source_iovec
        print(f"IOVec from Source integrity: {'PASS' if source_iovec_integrity_check else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"RawUncompressToIOVecFromSource failed: {e}")
    
    try:
        # Test RawUncompressToBuffers (simplified version)
        simple_buffers = snappy.raw_uncompress_to_buffers(compressed, buffer_sizes)
        print(f"RawUncompressToBuffers returned {len(simple_buffers)} buffers")
        print(f"Buffer lengths: {[len(buf) for buf in simple_buffers]}")
        
        # Reconstruct original data from buffers
        reconstructed_simple = b"".join(simple_buffers)
        simple_integrity_check = original_data == reconstructed_simple
        print(f"Simple buffers integrity: {'PASS' if simple_integrity_check else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"RawUncompressToBuffers failed: {e}")
    
    # Test IOVec compression
    print(f"\n--- Testing IOVec Compression ---")
    
    # Split the data into multiple buffers to test IOVec functionality
    data_buffers = [
        b"Hello, this is a test string for Snappy compression",
        b" and decompression! ",
        original_data[71:200],  # middle chunk
        original_data[200:]     # remaining data
    ]
    
    print(f"Number of input buffers: {len(data_buffers)}")
    print(f"Input buffer sizes: {[len(buf) for buf in data_buffers]}")
    print(f"Total input size: {sum(len(buf) for buf in data_buffers)} bytes")
    
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
        
        # Test scatter-gather decompression of IOVec compressed data
        print(f"\n--- Testing Scatter-Gather on IOVec Compressed Data ---")
        total_iovec_len = len(reconstructed_data)
        iovec_buffer_sizes = [len(buf) for buf in data_buffers]  # Use original buffer sizes
        
        try:
            scattered_buffers = snappy.raw_uncompress_to_iovec(compressed_iovec, iovec_buffer_sizes)
            print(f"Scattered decompression returned {len(scattered_buffers)} buffers")
            
            # Compare with original buffers
            for i, (original_buf, scattered_buf) in enumerate(zip(data_buffers, scattered_buffers)):
                match = original_buf == scattered_buf
                print(f"  Buffer {i} match: {'PASS' if match else 'FAIL'} ({len(original_buf)} vs {len(scattered_buf)} bytes)")
                
        except RuntimeError as e:
            print(f"Scatter-gather on IOVec data failed: {e}")
        
        # Compare with regular compression
        regular_compressed = snappy.compress(reconstructed_data)
        print(f"IOVec vs Regular size difference: {len(compressed_iovec) - len(regular_compressed)} bytes")
        
    except RuntimeError as e:
        print(f"IOVec compression test failed: {e}")
        print("Note: This may be expected if the WASM module doesn't include CompressFromIOVec")
    
    # Test edge cases for scatter-gather decompression
    print(f"\n--- Testing Edge Cases for Scatter-Gather ---")
    
    # Single buffer (should behave like regular decompression)
    try:
        single_buffer_result = snappy.raw_uncompress_to_buffers(compressed, [len(original_data)])
        single_check = original_data == single_buffer_result[0]
        print(f"Single buffer scatter-gather integrity: {'PASS' if single_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Single buffer scatter-gather failed: {e}")
    
    # Multiple small buffers
    try:
        small_buffer_sizes = [10] * (len(original_data) // 10) + [len(original_data) % 10]
        if small_buffer_sizes[-1] == 0:
            small_buffer_sizes = small_buffer_sizes[:-1]
        
        small_buffers_result = snappy.raw_uncompress_to_buffers(compressed, small_buffer_sizes)
        small_reconstructed = b"".join(small_buffers_result)
        small_check = original_data == small_reconstructed
        print(f"Many small buffers integrity: {'PASS' if small_check else 'FAIL'} ({len(small_buffers_result)} buffers)")
    except RuntimeError as e:
        print(f"Many small buffers test failed: {e}")
    
    # Test buffer size validation
    print(f"\n--- Testing Buffer Size Validation ---")
    
    try:
        # Try with wrong total size (should fail)
        wrong_sizes = [len(original_data) // 2, len(original_data) // 2 + 10]  # 10 bytes too many
        snappy.raw_uncompress_to_buffers(compressed, wrong_sizes)
        print("Wrong buffer size test: UNEXPECTED SUCCESS")
    except RuntimeError as e:
        print(f"Wrong buffer size test: EXPECTED FAILURE - {e}")
    
    try:
        # Try with zero-sized buffer (edge case)
        zero_sizes = [len(original_data), 0]
        zero_result = snappy.raw_uncompress_to_buffers(compressed, zero_sizes)
        zero_check = original_data == zero_result[0] and zero_result[1] == b""
        print(f"Zero-sized buffer test: {'PASS' if zero_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Zero-sized buffer test failed: {e}")
    
    print(f"\n--- Summary ---")
    print(f"WASM Module Version: {snappy.get_version()}")
    print("Available Functions:")
    print("  ✓ Compression: compress, compress_from_iovec")
    print("  ✓ Decompression: uncompress, raw_uncompress, raw_uncompress_from_source")
    print("  ✓ Scatter-Gather: raw_uncompress_to_iovec, raw_uncompress_to_iovec_from_source, raw_uncompress_to_buffers")
    print("  ✓ Validation: is_valid_compressed_buffer, is_valid_compressed")
    print("  ✓ Utilities: get_uncompressed_length, max_compressed_length, compression_info")