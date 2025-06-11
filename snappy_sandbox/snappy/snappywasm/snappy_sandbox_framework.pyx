# Update snappy_wrapper.pyx

import os
from wasm_sandbox_framework import WasmSandbox
from utils import create_wasm_imports
from validators import *

class SnappyWasm:
    def __init__(self, wasm_path=None):
        if not wasm_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            wasm_path = os.path.join(current_dir, "wasm", "non_faulty_snappy.wasm")
        
        self.sandbox = WasmSandbox(wasm_path, create_wasm_imports)
        mem_mgr = self.sandbox.get_memory_manager()
        self.memory = mem_mgr.memory

    def max_compressed_length(self, source_length: int) -> int:
        tainted_result = self.sandbox.invoke_sandbox_function(
            "MaxCompressedLength", 
            source_length
        )
        return tainted_result.verify(
            lambda x: validate_max_compressed_length(source_length, x)
        )
    
    def get_uncompressed_length(self, compressed_data: bytes) -> int:
        """Get the uncompressed length from compressed data"""
        mem_mgr = self.sandbox.get_memory_manager()
        
        compressed_len = len(compressed_data)
        compressed_offset = 0
        result_offset = compressed_len + 1024
        
        mem_mgr.write_buffer(compressed_offset, compressed_data)
        
        tainted_success = self.sandbox.invoke_sandbox_function(
            "GetUncompressedLength",
            compressed_offset,
            compressed_len,
            result_offset
        )
        
        success = tainted_success.verify(lambda x: x if x else RuntimeError("Failed to get uncompressed length"))
        
        # Read tainted result and verify
        tainted_length = mem_mgr.read_u32(result_offset)
        uncompressed_length = tainted_length.verify(
            lambda x: validate_uncompressed_length(compressed_len, x)
        )
        
        return uncompressed_length

    def compress(self, input_data: bytes, compression_level=None) -> bytes:
        mem_mgr = self.sandbox.get_memory_manager()
        
        max_out_len = self.max_compressed_length(len(input_data))
        input_len = len(input_data)
        
        # Define offsets
        input_offset = 0
        output_offset = input_len + 16  # leave a gap to prevent overwrite
        
        # Write input data to WASM memory
        mem_mgr.write_buffer(input_offset, input_data)
        
        # Choose function and call it
        if compression_level is not None:
            tainted_compressed_len = self.sandbox.invoke_sandbox_function(
                "CompressWithOptionsFromPtr",
                input_offset,
                input_len,
                output_offset,
                max_out_len,
                compression_level
            )
        else:
            tainted_compressed_len = self.sandbox.invoke_sandbox_function(
                "CompressFromPtr",
                input_offset,
                input_len,
                output_offset,
                max_out_len
            )
        
        # Verify compressed length
        compressed_len = tainted_compressed_len.verify(
            lambda x: validate_compressed_output(input_len, max_out_len, x) if x > 0 else RuntimeError("Compression failed")
        )
        
        # Read compressed data from WASM memory
        tainted_result = mem_mgr.read_buffer(output_offset, compressed_len)
        
        # Verify compressed data (you may want to add a validator for the actual compressed bytes)
        return tainted_result.verify(lambda x: x)

    def compress_source_sink(self, data: Union[str, bytes]) -> bytes:
        """Compress data using CompressFromSourceToSink function"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        input_len = len(data)
        
        # For very large data, fall back to regular compress method
        if input_len > 4000:  # Safe threshold
            return self.compress(data)
        
        mem_mgr = self.sandbox.get_memory_manager()
        max_out_len = self.max_compressed_length(input_len)
        
        # Memory offsets
        input_offset = 0
        output_offset = input_len + 1024
        
        # Write input data to WASM memory
        mem_mgr.write_buffer(input_offset, data)
        
        # Call compression function
        tainted_compressed_len = self.sandbox.invoke_sandbox_function(
            "CompressFromSourceToSink",
            input_offset,
            input_len,
            output_offset,
            max_out_len
        )
        
        # Verify compressed length
        compressed_len = tainted_compressed_len.verify(
            lambda x: x if x > 0 else RuntimeError("Compression failed")
        )
        
        # Read compressed data from WASM memory
        tainted_result = mem_mgr.read_buffer(output_offset, compressed_len)
        
        # Return verified result
        return tainted_result.verify(lambda x: x)

    def compress_from_iovec(self, data_buffers: List[Union[bytes, bytearray]], compression_level=-1) -> bytes:
        """
        Compress data from multiple buffers using Snappy's CompressFromIOVec functionality.
        
        Args:
            data_buffers: List of byte buffers to compress
            compression_level: Compression level (-1 for default)
            
        Returns:
            Compressed data as bytes
            
        Raises:
            RuntimeError: If compression fails or WASM function not available
        """
        if not data_buffers:
            return b''

        mem_mgr = self.sandbox.get_memory_manager()
        
        # Calculate total input length and max compressed length
        total_input_len = sum(len(buf) for buf in data_buffers)
        max_out_len = self.max_compressed_length(total_input_len)
        
        # Memory layout calculations
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
            mem_mgr.write_u32(iovec_entry_offset, current_data_offset)      # pointer
            mem_mgr.write_u32(iovec_entry_offset + 4, buffer_len)           # length
            
            # Copy buffer data to WASM memory
            if buffer_len > 0:
                mem_mgr.write_buffer(current_data_offset, buffer)
            
            current_data_offset += buffer_len

        # Call CompressFromIOVec function
        if compression_level == -1:
            tainted_compressed_len = self.sandbox.invoke_sandbox_function(
                "CompressFromIOVec",
                iovec_offset,
                iovec_count,
                output_offset,
                max_out_len
            )
        else:
            tainted_compressed_len = self.sandbox.invoke_sandbox_function(
                "CompressFromIOVecWithOptions",
                iovec_offset,
                iovec_count,
                output_offset,
                max_out_len,
                compression_level
            )
        
        # Verify compressed length
        compressed_len = tainted_compressed_len.verify(
            lambda x: validate_iovec_compressed_output(total_input_len, max_out_len, x) if x > 0 else RuntimeError("IOVec compression failed")
        )
        
        # Read compressed result
        tainted_result = mem_mgr.read_buffer(output_offset, compressed_len)
        
        # Return verified result
        return tainted_result.verify(lambda x: x)

    def is_valid_compressed(self, compressed_data: bytes) -> bool:
        """
        Validate if the data is properly compressed with Snappy using the Source* abstraction.
        This uses IsValidCompressed which internally creates a ByteArraySource.
        """
        mem_mgr = self.sandbox.get_memory_manager()
        
        compressed_len = len(compressed_data)
        compressed_offset = 0

        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)

        # Call validation function with Source* abstraction
        tainted_is_valid = self.sandbox.invoke_sandbox_function(
            "IsValidCompressed",
            compressed_offset,
            compressed_len
        )
        
        # Verify and convert to bool
        is_valid = tainted_is_valid.verify(
            lambda x: validate_is_valid_compressed_result(compressed_data, bool(x))
        )
        
        return is_valid

    def is_valid_compressed_buffer(self, compressed_data: bytes) -> bool:
        """Validate if the data is properly compressed with Snappy"""
        mem_mgr = self.sandbox.get_memory_manager()
        
        compressed_len = len(compressed_data)
        compressed_offset = 0
        
        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)
        
        # Call validation function (returns 1 for valid, 0 for invalid in WASM)
        tainted_is_valid = self.sandbox.invoke_sandbox_function(
            "IsValidCompressedBuffer",
            compressed_offset,
            compressed_len
        )
        
        # Verify and convert to bool
        is_valid = tainted_is_valid.verify(
            lambda x: validate_is_valid_compressed_buffer_result(compressed_data, bool(x))
        )
        
        return is_valid

    def uncompress(self, compressed_data: bytes) -> bytes:
        """Uncompress data using Snappy WASM"""
        mem_mgr = self.sandbox.get_memory_manager()
        
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

        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)

        # Call uncompress function
        tainted_actual_len = self.sandbox.invoke_sandbox_function(
            "UncompressFromPtr",
            compressed_offset,
            compressed_len,
            output_offset,
            uncompressed_length
        )
        
        # Verify actual uncompressed length
        actual_uncompressed_len = tainted_actual_len.verify(
            lambda x: validate_uncompress_output(compressed_len, uncompressed_length, x) if x > 0 else RuntimeError("Decompression failed")
        )

        # Read uncompressed data from WASM memory
        tainted_result = mem_mgr.read_buffer(output_offset, actual_uncompressed_len)
        
        # Return verified result
        return tainted_result.verify(lambda x: x)

    def get_uncompressed_length(self, compressed_data: bytes) -> int:
        """Get the uncompressed length from compressed data"""
        mem_mgr = self.sandbox.get_memory_manager()
        
        compressed_len = len(compressed_data)
        compressed_offset = 0
        result_offset = compressed_len + 1024  # offset for storing the result
        
        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)
        
        # Call the function
        tainted_success = self.sandbox.invoke_sandbox_function(
            "GetUncompressedLength",
            compressed_offset,
            compressed_len,
            result_offset
        )
        
        # Verify success
        success = tainted_success.verify(lambda x: x if x else RuntimeError("Failed to get uncompressed length"))
        
        # Read the result
        tainted_length = mem_mgr.read_u32(result_offset)
        uncompressed_length = tainted_length.verify(
            lambda x: validate_uncompressed_length(compressed_len, x)
        )
        
        return uncompressed_length

    def raw_compress(self, input_data: bytes) -> bytes:
        """
        Compress raw data using the sandboxed Snappy RawCompress function.
        
        Args:
            input_data: Raw bytes to compress
            
        Returns:
            Compressed bytes, or empty bytes if compression fails
        """
        if not input_data:
            return b''

        mem_mgr = self.sandbox.get_memory_manager()
        
        input_len = len(input_data)
        
        # Estimate maximum compressed size (Snappy's worst case is roughly input + input/6 + 32)
        max_compressed_len = input_len + (input_len // 6) + 32
        
        # Define offsets in WASM memory
        input_offset = 0
        output_offset = input_len + 16  # leave gap to prevent overwrite
        length_offset = output_offset + max_compressed_len + 16  # offset for compressed length

        try:
            # Write input data to WASM memory
            mem_mgr.write_buffer(input_offset, input_data)
            
            # Call raw compress function
            # Function signature: void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length)
            tainted_result = self.sandbox.invoke_sandbox_function(
                "RawCompress",
                input_offset,
                input_len,
                output_offset,
                length_offset
            )
            
            # Read the actual compressed length from memory
            tainted_actual_len = mem_mgr.read_u32(length_offset)
            actual_compressed_len = tainted_actual_len.verify(
                lambda x: x if (x > 0 and x <= max_compressed_len) else 0
            )
            
            if actual_compressed_len == 0:
                return b''

            # Read compressed data from WASM memory
            tainted_compressed = mem_mgr.read_buffer(output_offset, actual_compressed_len)
            
            # Verify and return compressed data
            return tainted_compressed.verify(
                lambda x: validate_raw_compress_output(input_data, x, max_compressed_len)
            )
            
        except Exception as e:
            print(f"Compression failed: {str(e)}")
            return b''

    def raw_uncompress(self, compressed_data: bytes, uncompressed_buffer: bytearray) -> bool:
        if not compressed_data or len(uncompressed_buffer) == 0:
            return False

        mem_mgr = self.sandbox.get_memory_manager()
        
        compressed_len = len(compressed_data)
        uncompressed_len = len(uncompressed_buffer)

        # Define offsets in WASM memory
        compressed_offset = 0
        output_offset = compressed_len + 16  # leave gap to prevent overwrite

        try:
            # Write compressed data to WASM memory
            mem_mgr.write_buffer(compressed_offset, compressed_data)

            # Call raw uncompress function
            # Function signature: bool RawUncompress(const char* compressed, size_t compressed_length, char* uncompressed)
            tainted_success = self.sandbox.invoke_sandbox_function(
                "RawUncompress",
                compressed_offset,
                compressed_len,
                output_offset
            )
            
            # Verify success
            success = tainted_success.verify(lambda x: bool(x))
            
            if not success:
                return False

            # Read uncompressed data from WASM memory
            tainted_uncompressed = mem_mgr.read_buffer(output_offset, uncompressed_len)
            
            # Simple validator - just return the bytes as-is
            verified_data = tainted_uncompressed.verify(lambda x: validate_raw_uncompress_buffer_output(compressed_data, x, success))
            
            # Copy verified data to the output buffer
            uncompressed_buffer[:] = verified_data
            
            # Call the original validator if needed
            return True
            
        except Exception as e:
            return False

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

        mem_mgr = self.sandbox.get_memory_manager()
        
        total_in = sum(len(b) for b in data_buffers)
        iov_cnt = len(data_buffers)
        
        # Memory layout
        iov_off = 0
        entry = 8  # 4‑byte ptr + 4‑byte len
        data_off = iov_off + iov_cnt * entry + 64
        out_off = data_off + total_in + 1024
        len_ptr = out_off + self.max_compressed_length(total_in) + 16

        # Write iovec entries and the buffers
        curr = data_off
        for i, buf in enumerate(data_buffers):
            L = len(buf)
            # Write iovec entry (ptr, len)
            mem_mgr.write_u32(iov_off + i*entry + 0, curr)  # ptr field
            mem_mgr.write_u32(iov_off + i*entry + 4, L)     # len field
            
            # Write data
            if L:
                mem_mgr.write_buffer(curr, buf)
            curr += L

        # Invoke the raw‐compress function
        tainted_result = self.sandbox.invoke_sandbox_function(
            "RawCompressFromIOVec",
            iov_off,
            iov_cnt,
            total_in,
            out_off,
            len_ptr
        )

        # Read back compressed length
        tainted_comp_len = mem_mgr.read_u32(len_ptr)
        comp_len = tainted_comp_len.verify(lambda x: x if x > 0 else RuntimeError("Compression failed"))

        # Read compressed data
        tainted_compressed = mem_mgr.read_buffer(out_off, comp_len)
        
        # Verify and return
        return tainted_compressed.verify(lambda x: x)


    def get_min_compression_level(self) -> int:
        tainted_result = self.sandbox.invoke_sandbox_function("GetMinCompressionLevel")
        return tainted_result.verify(
            lambda x: validate_compression_level_result(x, "Min Compression Level")
        )

    def get_max_compression_level(self) -> int:
        tainted_result = self.sandbox.invoke_sandbox_function("GetMaxCompressionLevel")
        return tainted_result.verify(
            lambda x: validate_compression_level_result(x, "Max Compression Level")
        )

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
        lo = self.get_min_compression_level()
        hi = self.get_max_compression_level()
        if options < lo or options > hi:
            raise RuntimeError(f"Invalid compression option {options}")

        mem_mgr = self.sandbox.get_memory_manager()
        
        total_in = sum(len(b) for b in data_buffers)
        iov_cnt = len(data_buffers)
        
        # Memory layout
        iov_off = 0
        entry = 8
        data_off = iov_off + iov_cnt * entry + 64
        out_off = data_off + total_in + 1024
        len_ptr = out_off + self.max_compressed_length(total_in) + 16

        # Write iovec entries and data
        curr = data_off
        for i, buf in enumerate(data_buffers):
            L = len(buf)
            mem_mgr.write_u32(iov_off + i*entry + 0, curr)  # ptr
            mem_mgr.write_u32(iov_off + i*entry + 4, L)     # len
            if L:
                mem_mgr.write_buffer(curr, buf)
            curr += L

        # Invoke the raw‐compress with options
        tainted_result = self.sandbox.invoke_sandbox_function(
            "RawCompressFromIOVecWithOptions",
            iov_off,
            iov_cnt,
            total_in,
            out_off,
            len_ptr,
            options
        )

        # Read compressed length
        tainted_comp_len = mem_mgr.read_u32(len_ptr)
        comp_len = tainted_comp_len.verify(lambda x: x if x > 0 else RuntimeError("Compression failed"))

        # Read compressed data
        tainted_compressed = mem_mgr.read_buffer(out_off, comp_len)
        max_out_len = self.max_compressed_length(total_in)
        
        # Verify and return
        return tainted_compressed.verify(
            lambda x: validate_raw_compress_from_iovec_with_options_output(
                data_buffers, x, max_out_len, options, lo, hi
            )
        )

    def raw_uncompress_from_source(self, compressed_data: bytes) -> bytes:
        """
        Raw uncompress data using Snappy's RawUncompressFromSource functionality.
        This uses the Source* abstraction internally.
        """
        mem_mgr = self.sandbox.get_memory_manager()
        
        # Get the expected uncompressed length
        uncompressed_length = self.get_uncompressed_length(compressed_data)
        compressed_len = len(compressed_data)

        # Define offsets
        compressed_offset = 0
        output_offset = compressed_len + 1024

        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)

        # Call raw uncompress from source function
        tainted_success = self.sandbox.invoke_sandbox_function(
            "RawUncompressFromSource",
            compressed_offset,
            compressed_len,
            output_offset
        )
        
        # Verify success
        success = tainted_success.verify(
            lambda x: x if x else RuntimeError("Raw decompression from source failed")
        )

        # Read uncompressed data from WASM memory
        tainted_result = mem_mgr.read_buffer(output_offset, uncompressed_length)
        
        # Verify and return
        return tainted_result.verify(lambda x: x)

    def raw_uncompress_to_iovec(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using Snappy's RawUncompressToIOVec functionality.
        This is scatter-gather decompression - the compressed data is decompressed directly into
        multiple non-contiguous output buffers.
        """
        if not buffer_sizes:
            return []

        mem_mgr = self.sandbox.get_memory_manager()
        
        # Validate that total buffer size matches expected uncompressed length
        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Memory layout calculations
        iovec_size = 8  # sizeof(struct iovec) in WASM
        iovec_array_size = buffer_count * iovec_size
        
        # Calculate offsets
        compressed_offset = 0
        iovec_offset = compressed_len + 64  # padding for alignment
        buffers_start_offset = iovec_offset + iovec_array_size + 64
        
        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)
        
        # Build iovec array
        current_buffer_offset = buffers_start_offset
        
        for i, buffer_size in enumerate(buffer_sizes):
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            
            # Write iovec structure (ptr, len)
            mem_mgr.write_u32(iovec_entry_offset, current_buffer_offset)      # pointer
            mem_mgr.write_u32(iovec_entry_offset + 4, buffer_size)           # length
            
            current_buffer_offset += buffer_size

        # Call RawUncompressToIOVec function
        tainted_success = self.sandbox.invoke_sandbox_function(
            "RawUncompressToIOVec",
            compressed_offset,
            compressed_len,
            iovec_offset,
            buffer_count
        )
        
        # Verify success
        success = tainted_success.verify(
            lambda x: x if x else RuntimeError("IOVec raw decompression failed")
        )

        # Read results from each buffer
        results = []
        current_buffer_offset = buffers_start_offset
        
        for buffer_size in buffer_sizes:
            tainted_buffer = mem_mgr.read_buffer(current_buffer_offset, buffer_size)
            results.append(tainted_buffer.verify(lambda x: x))
            current_buffer_offset += buffer_size

        validate_raw_uncompress_to_iovec_output(expected_length, results)
        return results

    def raw_uncompress_to_iovec_from_source(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using Snappy's RawUncompressToIOVecFromSource functionality.
        This uses the Source* abstraction internally and provides scatter-gather decompression.
        """
        if not buffer_sizes:
            return []

        mem_mgr = self.sandbox.get_memory_manager()
        
        # Validate buffer sizes
        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Memory layout
        iovec_size = 8
        iovec_array_size = buffer_count * iovec_size
        
        compressed_offset = 0
        iovec_offset = compressed_len + 64
        buffers_start_offset = iovec_offset + iovec_array_size + 64
        
        # Write compressed data
        mem_mgr.write_buffer(compressed_offset, compressed_data)
        
        # Build iovec array
        current_buffer_offset = buffers_start_offset
        
        for i, buffer_size in enumerate(buffer_sizes):
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            mem_mgr.write_u32(iovec_entry_offset, current_buffer_offset)
            mem_mgr.write_u32(iovec_entry_offset + 4, buffer_size)
            current_buffer_offset += buffer_size

        # Call function
        tainted_success = self.sandbox.invoke_sandbox_function(
            "RawUncompressToIOVecFromSource",
            compressed_offset,
            compressed_len,
            iovec_offset,
            buffer_count
        )
        
        success = tainted_success.verify(
            lambda x: x if x else RuntimeError("IOVec raw decompression from source failed")
        )

        # Read results
        results = []
        current_buffer_offset = buffers_start_offset
        
        for buffer_size in buffer_sizes:
            tainted_buffer = mem_mgr.read_buffer(current_buffer_offset, buffer_size)
            results.append(tainted_buffer.verify(lambda x: x))
            current_buffer_offset += buffer_size

        validate_raw_uncompress_to_iovec_output(expected_length, results)
        return results

    def raw_uncompress_to_buffers(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        """
        Decompress data into multiple separate buffers using the simplified RawUncompressToBuffers functionality.
        This is an easier-to-use version that doesn't require complex iovec handling.
        """
        if not buffer_sizes:
            return []

        mem_mgr = self.sandbox.get_memory_manager()
        
        # Validate buffer sizes
        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        # Memory layout
        lengths_array_size = buffer_count * 4  # sizeof(size_t) in WASM (32-bit)
        
        # Calculate offsets
        compressed_offset = 0
        lengths_array_offset = compressed_len + 64
        output_buffer_offset = lengths_array_offset + lengths_array_size + 64
        
        # Write compressed data
        mem_mgr.write_buffer(compressed_offset, compressed_data)
        
        # Write buffer sizes array
        for i, size in enumerate(buffer_sizes):
            mem_mgr.write_u32(lengths_array_offset + (i * 4), size)

        # Call function
        tainted_success = self.sandbox.invoke_sandbox_function(
            "RawUncompressToBuffers",
            compressed_offset,
            compressed_len,
            output_buffer_offset,
            lengths_array_offset,
            buffer_count
        )
        
        success = tainted_success.verify(
            lambda x: x if x else RuntimeError("Simplified raw decompression to buffers failed")
        )

        # Read results from contiguous buffer
        results = []
        current_offset = 0
        
        for buffer_size in buffer_sizes:
            tainted_buffer = mem_mgr.read_buffer(output_buffer_offset + current_offset, buffer_size)
            results.append(tainted_buffer.verify(lambda x: x))
            current_offset += buffer_size
        
        validate_raw_uncompress_to_buffers_output(expected_length, buffer_sizes, results)
        return results

    def uncompress_source_sink(self, compressed_data: bytes) -> bytes:
        """
        Uncompress data using Source/Sink abstraction.
        Uses: int UncompressSourceSink(const char* compressed, size_t compressed_length, char* output, size_t max_output_length)
        """
        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        mem_mgr = self.sandbox.get_memory_manager()
        
        # Get expected uncompressed length
        try:
            uncompressed_length = self.get_uncompressed_length(compressed_data)
        except RuntimeError:
            # Fallback estimation
            uncompressed_length = len(compressed_data) * 4

        compressed_len = len(compressed_data)
        
        # Calculate safe memory offsets
        compressed_offset = 0
        output_offset = compressed_len + 2048  # Increased spacing
        
        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)

        # Call UncompressSourceSink function
        tainted_bytes_written = self.sandbox.invoke_sandbox_function(
            "UncompressSourceSink",
            compressed_offset,
            compressed_len,
            output_offset,
            uncompressed_length
        )
        
        # Verify bytes written
        bytes_written = tainted_bytes_written.verify(
            lambda x: x if x > 0 and x <= uncompressed_length else RuntimeError(f"Source/Sink decompression failed or invalid result: {x}")
        )

        # Read the uncompressed data
        tainted_result = mem_mgr.read_buffer(output_offset, bytes_written)
        
        # Return verified result
        return tainted_result.verify(lambda x: x)

    def uncompress_as_much_as_possible_source_sink(self, compressed_data: bytes, max_output_size: int = None) -> bytes:
        """
        Uncompress as much data as possible using Source/Sink abstraction.
        Uses: size_t UncompressAsMuchAsPossibleSourceSink(const char* compressed, size_t compressed_length, char* output, size_t max_output_length)
        """
        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        mem_mgr = self.sandbox.get_memory_manager()
        
        # Determine output buffer size
        if max_output_size is None:
            try:
                max_output_size = self.get_uncompressed_length(compressed_data)
            except RuntimeError:
                # Fallback estimation
                max_output_size = len(compressed_data) * 4
        
        # Handle edge case
        if max_output_size <= 0:
            return b""

        compressed_len = len(compressed_data)
        
        # Calculate safe memory offsets
        compressed_offset = 0
        output_offset = compressed_len + 2048
        
        # Write compressed data to WASM memory
        mem_mgr.write_buffer(compressed_offset, compressed_data)

        # Call UncompressAsMuchAsPossibleSourceSink function
        tainted_bytes_written = self.sandbox.invoke_sandbox_function(
            "UncompressAsMuchAsPossibleSourceSink",
            compressed_offset,
            compressed_len,
            output_offset,
            max_output_size
        )
        
        # Verify bytes written (0 is acceptable for partial decompression)
        bytes_written = tainted_bytes_written.verify(
            lambda x: x if x >= 0 and x <= max_output_size else RuntimeError(f"Partial decompression failed or invalid result: {x}")
        )

        # Handle case where no bytes were written
        if bytes_written == 0:
            return b""

        # Read the uncompressed data
        tainted_result = mem_mgr.read_buffer(output_offset, bytes_written)
        
        # Return verified result
        return tainted_result.verify(lambda x: x)

    def get_version(self) -> int:
        try:
            tainted_version = self.sandbox.invoke_sandbox_function("GetVersion")
            return tainted_version.verify(lambda x: x)
        except RuntimeError:
            return 0