import os
import struct
from wasmtime import Store, Module, Instance, Func
from .utils import create_wasm_imports
import ctypes
from typing import List, Union
from .validators import *

class SnappyWasm:
    def __init__(self, wasm_path=None):
        if not wasm_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            wasm_path = os.path.join(current_dir, "wasm", "snappy.wasm")

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
        res = func(self.store, source_length)
        validate_max_compressed_length(source_length, res)
        return res

    def compress_source_sink(self, data: Union[str, bytes]) -> bytes:
        """Compress data using CompressFromSourceToSink function"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        func = self.exports.get("CompressFromSourceToSink")
        if not func:
            raise RuntimeError("CompressFromSourceToSink not found")
        
        input_len = len(data)
        
        # For very large data, fall back to regular compress method
        if input_len > 4000:  # Safe threshold
            return self.compress(data)
        
        max_out_len = self.max_compressed_length(input_len)
        
        # Memory offsets
        input_offset = 0
        output_offset = input_len + 1024
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        
        # Copy input data
        input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(data)
        ctypes.memmove(raw_addr + input_offset, input_array, input_len)
        
        # Call compression
        compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len)
        
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")
        
        # Copy result
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)
        
        return bytes(result)

    def compress_source_sink_with_options(self, data: Union[str, bytes], compression_level: int) -> bytes:
        """Compress data using CompressFromSourceToSinkWithOptions function"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        func = self.exports.get("CompressFromSourceToSinkWithOptions")
        if not func:
            raise RuntimeError("CompressFromSourceToSinkWithOptions not found")
        
        input_len = len(data)
        
        # For very large data, fall back to regular compress method
        if input_len > 4000:
            return self.compress(data, compression_level)
        
        max_out_len = self.max_compressed_length(input_len)
        
        # Memory offsets
        input_offset = 0
        output_offset = input_len + 1024
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        
        # Copy input data
        input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(data)
        ctypes.memmove(raw_addr + input_offset, input_array, input_len)
        
        # Call compression with options
        compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len, compression_level)
        
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")
        
        # Copy result
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)
        
        return bytes(result)

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
        validate_uncompressed_length(compressed_len, uncompressed_length)
        return uncompressed_length

    def compress(self, input_data: bytes, compression_level=None) -> bytes:
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
        output_offset = input_len + 16  # leave a gap to prevent overwrite

        # Convert input to byte array
        src_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # Copy input data into WASM memory
        ctypes.memmove(raw_addr + input_offset, src_array, input_len)

        # Call compress function - add compression_level parameter when needed
        if compression_level is not None:
            compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len, compression_level)
        else:
            compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len)
            
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")

        validate_compressed_output(input_len, max_out_len, compressed_len)

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
        
        validate_iovec_compressed_output(total_input_len, max_out_len, compressed_len)

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
        
        validate_uncompress_output(compressed_len, uncompressed_length, actual_uncompressed_len)

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
        
        res = bytes(result)
        validate_raw_uncompressed_output(uncompressed_length, res)
        return res

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

        validate_raw_uncompress_to_iovec_output(expected_length, results)

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

        validate_raw_uncompress_to_iovec_output(expected_length, results)

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
        
        validate_raw_uncompress_to_buffers_output(expected_length, buffer_sizes, results)

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
        res = bool(is_valid)
        validate_is_valid_compressed_buffer_result(compressed_data, res)

        return res

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
        validate_is_valid_compressed_result(compressed_data, is_valid)

        return bool(is_valid)

    def get_min_compression_level(self) -> int:
        func = self.exports.get("GetMinCompressionLevel")
        if not func:
            return 1  # Default fallback
        result = func(self.store)
        validate_compression_level_result(result, "Min Compression Level")
        return result

    def get_max_compression_level(self) -> int:
        func = self.exports.get("GetMaxCompressionLevel")
        if not func:
            return 2  # Default fallback
        result = func(self.store)
        validate_compression_level_result(result, "Max Compression Level")
        return result

    def get_default_compression_level(self) -> int:
        func = self.exports.get("GetDefaultCompressionLevel")
        if not func:
            return 1  # Default fallback
        return func(self.store)

    def get_compression_info(self) -> dict:
        info = {
            "min_level": self.get_min_compression_level(),
            "max_level": self.get_max_compression_level(),
            "default_level": self.get_default_compression_level(),
        }
        info["supported_levels"] = list(range(info["min_level"], info["max_level"] + 1))
        validate_compression_info(info)
        return info

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
        output_offset = compressed_len + 16  # leave gap to prevent overwrite

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
            validate_raw_uncompress_buffer_output(compressed_data, uncompressed_buffer, success)
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
            validate_raw_uncompress_to_iovec_from_source_output(compressed_data, buffer_sizes, results,expected_total_len=expected_length if 'expected_length' in locals() else None)
            return results
            
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"IOVec decompression from source failed: {str(e)}")
    
    def raw_compress(self, input_data: bytes) -> bytes:
        """
        Compress raw data using the sandboxed Snappy RawCompress function.
        
        Args:
            input_data: Raw bytes to compress
            
        Returns:
            Compressed bytes, or empty bytes if compression fails
        """
        if not self.memory:
            return b''

        func = self.exports.get("RawCompress")
        if not func:
            return b''

        if not input_data:
            return b''

        import struct
        input_len = len(input_data)
        
        # Estimate maximum compressed size (Snappy's worst case is roughly input + input/6 + 32)
        max_compressed_len = input_len + (input_len // 6) + 32
        
        # Define offsets in WASM memory
        input_offset = 0
        output_offset = input_len + 16  # leave gap to prevent overwrite
        length_offset = output_offset + max_compressed_len + 16  # offset for compressed length

        try:
            # Convert input data to byte array
            input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

            # Access WASM memory
            mem_ptr = self.memory.data_ptr(self.store)
            raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

            # Copy input data into WASM memory
            ctypes.memmove(raw_addr + input_offset, input_array, input_len)
            
            # Call raw compress function
            # Function signature: void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length)
            func(self.store, input_offset, input_len, output_offset, length_offset)
            
            # Read the actual compressed length from memory
            actual_len_byte = (ctypes.c_ubyte * 4)()
            ctypes.memmove(actual_len_byte, raw_addr + length_offset, 4)
            actual_compressed_len = struct.unpack('<I', bytes(actual_len_byte))[0]
            
            if actual_compressed_len == 0 or actual_compressed_len > max_compressed_len:
                return b''

            # Copy compressed data back from WASM memory
            result_array = (ctypes.c_ubyte * actual_compressed_len)()
            ctypes.memmove(result_array, raw_addr + output_offset, actual_compressed_len)
            res = bytes(result_array)
            validate_raw_compress_output(input_data, res, max_compressed_len)
            return res
            
        except Exception as e:
            print(f"Compression failed: {str(e)}")
            return b''

    def raw_compress_with_options(self, input_data: bytes, compression_level: int = 1) -> bytes:
        """
        Compress raw data using the sandboxed Snappy RawCompress function with compression options.
        
        Args:
            input_data: Raw bytes to compress
            compression_level: Compression level (typically 1-9, but Snappy may have different ranges)
            
        Returns:
            Compressed bytes, or empty bytes if compression fails
        """
        if not self.memory:
            return b''

        func = self.exports.get("RawCompressWithOptions")
        if not func:
            return b''

        if not input_data:
            return b''

        import struct
        input_len = len(input_data)
        
        # Estimate maximum compressed size
        max_compressed_len = input_len + (input_len // 6) + 32
        
        # Define offsets in WASM memory
        input_offset = 0
        output_offset = input_len + 16  # leave gap to prevent overwrite
        length_offset = output_offset + max_compressed_len + 16  # offset for compressed length

        try:
            # Convert input data to byte array
            input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

            # Access WASM memory
            mem_ptr = self.memory.data_ptr(self.store)
            raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

            # Copy input data into WASM memory
            ctypes.memmove(raw_addr + input_offset, input_array, input_len)

            # Call raw compress function with options
            # Function signature: void RawCompressWithOptions(const char* input, size_t input_length, char* compressed, size_t* compressed_length, int compression_level)
            func(self.store, input_offset, input_len, output_offset, length_offset, compression_level)
            
            # Read the actual compressed length from memory
            actual_len_byte = (ctypes.c_ubyte * 4)()
            ctypes.memmove(actual_len_byte, raw_addr + length_offset, 4)
            actual_compressed_len = struct.unpack('<I', actual_len_byte)[0]
            
            if actual_compressed_len == 0 or actual_compressed_len > max_compressed_len:
                return b''

            # Copy compressed data back from WASM memory
            result_array = (ctypes.c_ubyte * actual_compressed_len)()
            ctypes.memmove(result_array, raw_addr + output_offset, actual_compressed_len)
            result = bytes(result_array)
            validate_raw_compress_with_options_output(input_data, result, max_compressed_len, compression_level)
            return result
            
        except Exception:
            return b''

    def raw_compress_from_iovec(self, data_buffers: List[Union[bytes, bytearray]]) -> bytes:
        """
        void RawCompressFromIOVec(const struct iovec* iov,
                                  size_t iov_cnt,
                                  size_t uncompressed_length,
                                  char* compressed,
                                  size_t* compressed_length);
        """
        if not data_buffers:
            raise RuntimeError("No buffers provided")

        fn = self.exports.get("RawCompressFromIOVec")
        if not fn:
            raise RuntimeError("RawCompressFromIOVec not exported")

        total_in = sum(len(b) for b in data_buffers)
        iov_cnt = len(data_buffers)
        iov_off = 0
        entry = 8  # 4‑byte ptr + 4‑byte len
        data_off = iov_off + iov_cnt * entry + 64
        out_off = data_off + total_in + 1024
        len_ptr = out_off + self.max_compressed_length(total_in) + 16

        # base address of linear memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_base = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        # write iovec entries and the buffers
        curr = data_off
        for i, buf in enumerate(data_buffers):
            L = len(buf)
            # ptr field
            ctypes.memmove(
                raw_base + iov_off + i*entry + 0,
                (ctypes.c_ubyte * 4).from_buffer_copy(struct.pack("<I", curr)),
                4
            )
            # len field
            ctypes.memmove(
                raw_base + iov_off + i*entry + 4,
                (ctypes.c_ubyte * 4).from_buffer_copy(struct.pack("<I", L)),
                4
            )
            # data
            if L:
                ctypes.memmove(
                    raw_base + curr,
                    (ctypes.c_ubyte * L).from_buffer_copy(buf),
                    L
                )
            curr += L

        # invoke the raw‐compress
        fn(self.store, iov_off, iov_cnt, total_in, out_off, len_ptr)

        # read back compressed length (uint32)
        tmp = (ctypes.c_ubyte * 4)()
        ctypes.memmove(tmp, raw_base + len_ptr, 4)
        comp_len = struct.unpack("<I", bytes(tmp))[0]

        # copy out compressed bytes
        result = bytearray(comp_len)
        ctypes.memmove(
            (ctypes.c_ubyte * comp_len).from_buffer(result),
            raw_base + out_off,
            comp_len
        )
        return bytes(result)

    def raw_compress_from_iovec_with_options(
        self,
        data_buffers: List[Union[bytes, bytearray]],
        options: int
    ) -> bytes:
        """
        void RawCompressFromIOVec(const struct iovec* iov,
                                  size_t iov_cnt,
                                  size_t uncompressed_length,
                                  char* compressed,
                                  size_t* compressed_length,
                                  CompressionOptions options);
        """
        if not data_buffers:
            raise RuntimeError("No buffers provided")

        # validate options against WASM exports
        lo = self.exports.get("GetMinCompressionLevel", lambda store: 0)(self.store)
        hi = self.exports.get("GetMaxCompressionLevel", lambda store: lo)(self.store)
        if options < lo or options > hi:
            raise RuntimeError(f"Invalid compression option {options}")

        fn = self.exports.get("RawCompressFromIOVecWithOptions")
        if not fn:
            raise RuntimeError("RawCompressFromIOVecWithOptions not exported")

        total_in = sum(len(b) for b in data_buffers)
        iov_cnt = len(data_buffers)
        iov_off = 0
        entry = 8
        data_off = iov_off + iov_cnt * entry + 64
        out_off = data_off + total_in + 1024
        len_ptr = out_off + self.max_compressed_length(total_in) + 16

        mem_ptr = self.memory.data_ptr(self.store)
        raw_base = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        curr = data_off
        for i, buf in enumerate(data_buffers):
            L = len(buf)
            ctypes.memmove(
                raw_base + iov_off + i*entry + 0,
                (ctypes.c_ubyte * 4).from_buffer_copy(struct.pack("<I", curr)),
                4
            )
            ctypes.memmove(
                raw_base + iov_off + i*entry + 4,
                (ctypes.c_ubyte * 4).from_buffer_copy(struct.pack("<I", L)),
                4
            )
            if L:
                ctypes.memmove(
                    raw_base + curr,
                    (ctypes.c_ubyte * L).from_buffer_copy(buf),
                    L
                )
            curr += L

        # invoke the raw‐compress with options
        fn(self.store, iov_off, iov_cnt, total_in, out_off, len_ptr, options)

        tmp = (ctypes.c_ubyte * 4)()
        ctypes.memmove(tmp, raw_base + len_ptr, 4)
        comp_len = struct.unpack("<I", bytes(tmp))[0]

        result = bytearray(comp_len)
        ctypes.memmove(
            (ctypes.c_ubyte * comp_len).from_buffer(result),
            raw_base + out_off,
            comp_len
        )
        result_bytes = bytes(result)
        max_out_len = self.max_compressed_length(total_in)
        validate_raw_compress_from_iovec_with_options_output(
            data_buffers,
            result_bytes,
            max_out_len,
            options,
            lo,
            hi
)
        return result_bytes
    
    def get_max_compressed_length(self, source_length: int) -> int:
        """
        Get the maximum possible compressed length for a given source length.
        This is useful for pre-allocating buffers.
        
        Args:
            source_length: Length of the source data
            
        Returns:
            Maximum possible compressed length, or 0 if function not available
        """
        if not self.memory:
            return 0

        func = self.exports.get("MaxCompressedLength")
        if not func:
            # Fallback estimation: Snappy's worst case is roughly input + input/6 + 32
            return source_length + (source_length // 6) + 32

        try:
            # Function signature: size_t MaxCompressedLength(size_t source_length)
            max_len = func(self.store, source_length)
            return max_len
            
        except Exception:
            # Fallback estimation
            return source_length + (source_length // 6) + 32

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
        
        validate_uncompress_output(compressed_len, uncompressed_length, actual_uncompressed_len)

        if actual_uncompressed_len <= 0:
            raise RuntimeError("Decompression failed")

        # Allocate output buffer
        result = bytearray(actual_uncompressed_len)
        result_array = (ctypes.c_ubyte * actual_uncompressed_len).from_buffer(result)

        # Copy back uncompressed result
        ctypes.memmove(result_array, raw_addr + output_offset, actual_uncompressed_len)

        return bytes(result)


    def uncompress_source_sink(self, compressed_data: bytes) -> bytes:
        """
        Uncompress data using Source/Sink abstraction.
        Uses: int UncompressSourceSink(const char* compressed, size_t compressed_length, char* output, size_t max_output_length)
        
        Args:
            compressed_data: The compressed data bytes
            
        Returns:
            bytes: The uncompressed data
            
        Raises:
            RuntimeError: If decompression fails or memory is not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressSourceSink")
        if not func:
            raise RuntimeError("UncompressSourceSink not found")

        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        # Get expected uncompressed length
        try:
            uncompressed_length = self.get_uncompressed_length(compressed_data)
        except RuntimeError:
            # Fallback estimation
            uncompressed_length = len(compressed_data) * 4

        compressed_len = len(compressed_data)
        
        # Calculate safe memory offsets with larger spacing to avoid memory issues
        compressed_offset = 0
        output_offset = compressed_len + 2048  # Increased spacing from 1024 to 2048
        
        # Check if we have enough memory (conservative check)
        total_needed = output_offset + uncompressed_length
        try:
            # Try different methods to get memory size
            if hasattr(self.memory, 'size'):
                memory_size = self.memory.size(self.store) * 65536  # Convert pages to bytes
            elif hasattr(self.memory, 'data_len'):
                memory_size = self.memory.data_len(self.store)
            else:
                memory_size = 16 * 1024 * 1024  # 16MB fallback
                
            if total_needed > memory_size:
                raise RuntimeError(f"Not enough WASM memory: need {total_needed}, have {memory_size}")
        except Exception:
            # If we can't check memory size, proceed carefully
            pass
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        try:
            # Copy compressed data into WASM memory
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

            # Call UncompressSourceSink function
            # IMPORTANT: The function returns the number of bytes written (int), not a boolean
            bytes_written = func(self.store, compressed_offset, compressed_len, output_offset, uncompressed_length)
            
            if bytes_written <= 0:
                raise RuntimeError("Source/Sink decompression failed")

            # Validate bytes_written doesn't exceed expected length
            if bytes_written > uncompressed_length:
                raise RuntimeError(f"Invalid decompression result: {bytes_written} > {uncompressed_length}")

            # Read the actual uncompressed data (use bytes_written, not uncompressed_length)
            result = bytearray(bytes_written)
            result_array = (ctypes.c_ubyte * bytes_written).from_buffer(result)
            ctypes.memmove(result_array, raw_addr + output_offset, bytes_written)

            return bytes(result)
            
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Source/Sink decompression error: {str(e)}")

    def uncompress_as_much_as_possible_source_sink(self, compressed_data: bytes, max_output_size: int = None) -> bytes:
        """
        Uncompress as much data as possible using Source/Sink abstraction.
        Uses: size_t UncompressAsMuchAsPossibleSourceSink(const char* compressed, size_t compressed_length, char* output, size_t max_output_length)
        
        This function is useful when you have limited output buffer space and want to
        decompress as much as possible without failing.
        
        Args:
            compressed_data: The compressed data bytes
            max_output_size: Maximum size of output buffer (if None, uses estimated size)
            
        Returns:
            bytes: The uncompressed data (may be partial if buffer was too small)
            
        Raises:
            RuntimeError: If decompression fails or memory is not available
        """
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressAsMuchAsPossibleSourceSink")
        if not func:
            raise RuntimeError("UncompressAsMuchAsPossibleSourceSink not found")

        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        # Determine output buffer size
        if max_output_size is None:
            try:
                max_output_size = self.get_uncompressed_length(compressed_data)
            except RuntimeError:
                # Fallback estimation
                max_output_size = len(compressed_data) * 4
        
        # Handle edge case of zero or negative buffer size
        if max_output_size <= 0:
            return b""

        compressed_len = len(compressed_data)
        
        # Calculate safe memory offsets with larger spacing
        compressed_offset = 0
        output_offset = compressed_len + 2048  # Increased spacing
        
        # Check memory constraints and adjust if necessary
        total_needed = output_offset + max_output_size
        try:
            # Try different methods to get memory size
            if hasattr(self.memory, 'size'):
                memory_size = self.memory.size(self.store) * 65536  # Convert pages to bytes
            elif hasattr(self.memory, 'data_len'):
                memory_size = self.memory.data_len(self.store)
            else:
                memory_size = 16 * 1024 * 1024  # 16MB fallback
            
            if total_needed > memory_size:
                # Reduce max_output_size to fit in available memory
                available_output_space = memory_size - output_offset - 1024  # Safety margin
                if available_output_space <= 0:
                    raise RuntimeError("Not enough WASM memory for decompression")
                max_output_size = min(max_output_size, available_output_space)
                
                if max_output_size <= 0:
                    return b""
        except Exception:
            # If we can't check memory size, proceed carefully
            pass
        
        # Access WASM memory
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        try:
            # Copy compressed data into WASM memory
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

            # Call UncompressAsMuchAsPossibleSourceSink function
            bytes_written = func(self.store, compressed_offset, compressed_len, output_offset, max_output_size)
            
            # bytes_written of 0 is acceptable for this function (partial decompression)
            if bytes_written < 0:
                raise RuntimeError("Source/Sink partial decompression failed")

            # Validate bytes_written doesn't exceed buffer size
            if bytes_written > max_output_size:
                raise RuntimeError(f"Invalid result: {bytes_written} > {max_output_size}")

            # Handle case where no bytes were written
            if bytes_written == 0:
                return b""

            # Read the uncompressed data (only the bytes that were actually written)
            result = bytearray(bytes_written)
            result_array = (ctypes.c_ubyte * bytes_written).from_buffer(result)
            ctypes.memmove(result_array, raw_addr + output_offset, bytes_written)

            return bytes(result)
            
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Partial decompression error: {str(e)}")


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