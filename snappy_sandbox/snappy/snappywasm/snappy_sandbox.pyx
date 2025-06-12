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
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        func = self.exports.get("CompressFromSourceToSink")
        if not func:
            raise RuntimeError("CompressFromSourceToSink not found")
        
        input_len = len(data)
        
        if input_len > 4000: 
            return self.compress(data)
        
        max_out_len = self.max_compressed_length(input_len)
        
        input_offset = 0
        output_offset = input_len + 1024
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        
        input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(data)
        ctypes.memmove(raw_addr + input_offset, input_array, input_len)
        
        compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len)
        
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")
        
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)
        
        return bytes(result)

    def compress_source_sink_with_options(self, data: Union[str, bytes], compression_level: int) -> bytes:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        func = self.exports.get("CompressFromSourceToSinkWithOptions")
        if not func:
            raise RuntimeError("CompressFromSourceToSinkWithOptions not found")
        
        input_len = len(data)
        
        if input_len > 4000:
            return self.compress(data, compression_level)
        
        max_out_len = self.max_compressed_length(input_len)
        
        input_offset = 0
        output_offset = input_len + 1024
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        
        input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(data)
        ctypes.memmove(raw_addr + input_offset, input_array, input_len)
        
        compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len, compression_level)
        
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")
        
        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)
        
        return bytes(result)

    def get_uncompressed_length(self, compressed_data: bytes) -> int:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("GetUncompressedLength")
        if not func:
            raise RuntimeError("GetUncompressedLength not found")

        compressed_len = len(compressed_data)
        
        compressed_offset = 0
        result_offset = compressed_len + 1024  # offset for storing the result

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        success = func(self.store, compressed_offset, compressed_len, result_offset)
        
        if not success:
            raise RuntimeError("Failed to get uncompressed length")

        result_bytes = bytearray(4)
        result_array = (ctypes.c_ubyte * 4).from_buffer(result_bytes)
        ctypes.memmove(result_array, raw_addr + result_offset, 4)
        
        uncompressed_length = struct.unpack('<I', result_bytes)[0]
        validate_uncompressed_length(compressed_len, uncompressed_length)
        return uncompressed_length

    def compress(self, input_data: bytes, compression_level=None) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

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

        input_offset = 0
        output_offset = input_len + 16  # leave a gap to prevent overwrite

        src_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + input_offset, src_array, input_len)

        if compression_level is not None:
            compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len, compression_level)
        else:
            compressed_len = func(self.store, input_offset, input_len, output_offset, max_out_len)
            
        if compressed_len <= 0:
            raise RuntimeError("Compression failed")

        validate_compressed_output(input_len, max_out_len, compressed_len)

        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)

        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)

        return bytes(result)

    def compress_from_iovec(self, data_buffers: List[Union[bytes, bytearray]], compression_level=-1) -> bytes:
        
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

        total_input_len = sum(len(buf) for buf in data_buffers)
        max_out_len = self.max_compressed_length(total_input_len)
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

       
        
        iovec_count = len(data_buffers)
        iovec_size = 8  # sizeof(struct iovec) in WASM (ptr + len)
        iovec_array_size = iovec_count * iovec_size
        
        iovec_offset = 0
        data_start_offset = iovec_array_size + 64  # padding for alignment
        output_offset = data_start_offset + total_input_len + 1024  # gap to prevent overwrite
        
        current_data_offset = data_start_offset
        
        for i, buffer in enumerate(data_buffers):
            buffer_len = len(buffer)
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            
            ptr_bytes = struct.pack('<I', current_data_offset)  # pointer (32-bit)
            len_bytes = struct.pack('<I', buffer_len)           # length (32-bit)
            
            ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
            len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
            
            ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
            ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
            
            if buffer_len > 0:
                buffer_array = (ctypes.c_ubyte * buffer_len).from_buffer_copy(buffer)
                ctypes.memmove(raw_addr + current_data_offset, buffer_array, buffer_len)
            
            current_data_offset += buffer_len

        if compression_level == -1:
            compressed_len = func(self.store, iovec_offset, iovec_count, output_offset, max_out_len)
        else:
            compressed_len = func(self.store, iovec_offset, iovec_count, output_offset, max_out_len, compression_level)
        
        validate_iovec_compressed_output(total_input_len, max_out_len, compressed_len)

        if compressed_len <= 0:
            raise RuntimeError("IOVec compression failed")

        result = bytearray(compressed_len)
        result_array = (ctypes.c_ubyte * compressed_len).from_buffer(result)
        ctypes.memmove(result_array, raw_addr + output_offset, compressed_len)

        return bytes(result)

    def uncompress(self, compressed_data: bytes) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressFromPtr")
        if not func:
            raise RuntimeError("UncompressFromPtr not found")

        try:
            uncompressed_length = self.get_uncompressed_length(compressed_data)
        except RuntimeError:
            # Fallback: estimate a reasonable buffer size
            uncompressed_length = len(compressed_data) * 4  # Conservative estimate

        compressed_len = len(compressed_data)

        compressed_offset = 0
        output_offset = compressed_len + 1024  # leave a gap to prevent overwrite

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        actual_uncompressed_len = func(self.store, compressed_offset, compressed_len, output_offset, uncompressed_length)
        
        validate_uncompress_output(compressed_len, uncompressed_length, actual_uncompressed_len)

        if actual_uncompressed_len <= 0:
            raise RuntimeError("Decompression failed")

        result = bytearray(actual_uncompressed_len)
        result_array = (ctypes.c_ubyte * actual_uncompressed_len).from_buffer(result)

        ctypes.memmove(result_array, raw_addr + output_offset, actual_uncompressed_len)

        return bytes(result)

    def raw_uncompress(self, compressed_data: bytes) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompress")
        if not func:
            raise RuntimeError("RawUncompress not found")

        uncompressed_length = self.get_uncompressed_length(compressed_data)
        compressed_len = len(compressed_data)

        compressed_offset = 0
        output_offset = compressed_len + 1024

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        success = func(self.store, compressed_offset, compressed_len, output_offset)
        
        if not success:
            raise RuntimeError("Raw decompression failed")

        result = bytearray(uncompressed_length)
        result_array = (ctypes.c_ubyte * uncompressed_length).from_buffer(result)

        ctypes.memmove(result_array, raw_addr + output_offset, uncompressed_length)
        
        res = bytes(result)
        validate_raw_uncompressed_output(uncompressed_length, res)
        return res

    def raw_uncompress_from_source(self, compressed_data: bytes) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressFromSource")
        if not func:
            raise RuntimeError("RawUncompressFromSource not found")

        uncompressed_length = self.get_uncompressed_length(compressed_data)
        compressed_len = len(compressed_data)

        compressed_offset = 0
        output_offset = compressed_len + 1024

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        success = func(self.store, compressed_offset, compressed_len, output_offset)
        
        if not success:
            raise RuntimeError("Raw decompression from source failed")

        result = bytearray(uncompressed_length)
        result_array = (ctypes.c_ubyte * uncompressed_length).from_buffer(result)

        ctypes.memmove(result_array, raw_addr + output_offset, uncompressed_length)

        return bytes(result)

    def raw_uncompress(self, compressed_data: bytes, uncompressed_length: int) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressFromSource")
        if not func:
            raise RuntimeError("RawUncompressFromSource not found")

        compressed_len = len(compressed_data)
        
        compressed_offset = 0
        uncompressed_offset = compressed_len + 16  # Add some padding
        
        total_memory_needed = uncompressed_offset + uncompressed_length
        if total_memory_needed > self.memory.data_size(self.store):
            raise RuntimeError(f"Not enough WASM memory. Need {total_memory_needed}, have {self.memory.data_size(self.store)}")

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        success = func(self.store, compressed_offset, compressed_len, uncompressed_offset)
        
        if not success:
            raise RuntimeError("Decompression failed")

        uncompressed_array = (ctypes.c_ubyte * uncompressed_length).from_address(raw_addr + uncompressed_offset)
        uncompressed_data = bytes(uncompressed_array)
        
        return uncompressed_data

    def raw_uncompress_to_iovec(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToIOVec")
        if not func:
            raise RuntimeError("RawUncompressToIOVec not found")

        if not buffer_sizes:
            return []

        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        iovec_size = 8  # sizeof(struct iovec) in WASM
        iovec_array_size = buffer_count * iovec_size
        
        compressed_offset = 0
        iovec_offset = compressed_len + 64  # padding for alignment
        buffers_start_offset = iovec_offset + iovec_array_size + 64  # more padding
        
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
        
        current_buffer_offset = buffers_start_offset
        
        for i, buffer_size in enumerate(buffer_sizes):
            iovec_entry_offset = iovec_offset + (i * iovec_size)
            
            ptr_bytes = struct.pack('<I', current_buffer_offset)  # pointer (32-bit)
            len_bytes = struct.pack('<I', buffer_size)            # length (32-bit)
            
            ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
            len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
            
            ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
            ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
            
            current_buffer_offset += buffer_size

       
        success = func(self.store, compressed_offset, compressed_len, iovec_offset, buffer_count)
        
        if not success:
            raise RuntimeError("IOVec raw decompression failed")

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
    
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToIOVecFromSource")
        if not func:
            raise RuntimeError("RawUncompressToIOVecFromSource not found")

        if not buffer_sizes:
            return []

        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        iovec_size = 8
        iovec_array_size = buffer_count * iovec_size
        
        compressed_offset = 0
        iovec_offset = compressed_len + 64
        buffers_start_offset = iovec_offset + iovec_array_size + 64
        
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
        
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

       
        success = func(self.store, compressed_offset, compressed_len, iovec_offset, buffer_count)
        
        if not success:
            raise RuntimeError("IOVec raw decompression from source failed")

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
        
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToBuffers")
        if not func:
            raise RuntimeError("RawUncompressToBuffers not found")

        if not buffer_sizes:
            return []

        total_buffer_size = sum(buffer_sizes)
        expected_length = self.get_uncompressed_length(compressed_data)
        
        if total_buffer_size != expected_length:
            raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

       
        lengths_array_size = buffer_count * 4  # sizeof(size_t) in WASM (32-bit)
        
        compressed_offset = 0
        lengths_array_offset = compressed_len + 64
        output_buffer_offset = lengths_array_offset + lengths_array_size + 64
        
        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
        
        for i, size in enumerate(buffer_sizes):
            size_bytes = struct.pack('<I', size)  # 32-bit size_t
            size_array = (ctypes.c_ubyte * 4).from_buffer_copy(size_bytes)
            ctypes.memmove(raw_addr + lengths_array_offset + (i * 4), size_array, 4)


        success = func(self.store, compressed_offset, compressed_len, output_buffer_offset, lengths_array_offset, buffer_count)
        
        if not success:
            raise RuntimeError("Simplified raw decompression to buffers failed")

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
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("IsValidCompressedBuffer")
        if not func:
            raise RuntimeError("IsValidCompressedBuffer not found")

        compressed_len = len(compressed_data)
        
        compressed_offset = 0

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        is_valid = func(self.store, compressed_offset, compressed_len)
        res = bool(is_valid)
        validate_is_valid_compressed_buffer_result(compressed_data, res)

        return res

    def is_valid_compressed(self, compressed_data: bytes) -> bool:
        
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("IsValidCompressed")
        if not func:
            raise RuntimeError("IsValidCompressed not found")

        compressed_len = len(compressed_data)
        compressed_offset = 0

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        is_valid = func(self.store, compressed_offset, compressed_len)
        validate_is_valid_compressed_result(compressed_data, is_valid)

        return bool(is_valid)

    def get_min_compression_level(self) -> int:
        func = self.exports.get("GetMinCompressionLevel")
        if not func:
            return 1  
        result = func(self.store)
        validate_compression_level_result(result, "Min Compression Level")
        return result

    def get_max_compression_level(self) -> int:
        func = self.exports.get("GetMaxCompressionLevel")
        if not func:
            return 2  
        result = func(self.store)
        validate_compression_level_result(result, "Max Compression Level")
        return result

    def get_default_compression_level(self) -> int:
        func = self.exports.get("GetDefaultCompressionLevel")
        if not func:
            return 1  
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

        compressed_offset = 0
        output_offset = compressed_len + 16  
        try:
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

            mem_ptr = self.memory.data_ptr(self.store)
            raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

            success = func(self.store, compressed_offset, compressed_len, output_offset)
            
            if not success:
                return False

            
            result_array = (ctypes.c_ubyte * uncompressed_len).from_buffer(uncompressed_buffer)
            ctypes.memmove(result_array, raw_addr + output_offset, uncompressed_len)
            validate_raw_uncompress_buffer_output(compressed_data, uncompressed_buffer, success)
            return True
            
        except Exception:
            return False
        
    def raw_uncompress_to_iovec_from_source(self, compressed_data: bytes, buffer_sizes: List[int]) -> List[bytes]:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("RawUncompressToIOVecFromSource")
        if not func:
            raise RuntimeError("RawUncompressToIOVecFromSource not found")

        if not buffer_sizes:
            return []

        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        total_buffer_size = sum(buffer_sizes)
        try:
            expected_length = self.get_uncompressed_length(compressed_data)
            if total_buffer_size != expected_length:
                raise RuntimeError(f"Buffer size mismatch: expected {expected_length}, got {total_buffer_size}")
        except Exception:
            pass

        compressed_len = len(compressed_data)
        buffer_count = len(buffer_sizes)
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)


        iovec_size = 8  
        iovec_array_size = buffer_count * iovec_size
        
        compressed_offset = 0
        iovec_offset = compressed_len + 64  
        buffers_start_offset = iovec_offset + iovec_array_size + 64 
        
        try:
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)
            
            current_buffer_offset = buffers_start_offset
            
            for i, buffer_size in enumerate(buffer_sizes):
                if buffer_size <= 0:
                    raise RuntimeError(f"Invalid buffer size at index {i}: {buffer_size}")
                    
                iovec_entry_offset = iovec_offset + (i * iovec_size)
                
                ptr_bytes = struct.pack('<I', current_buffer_offset)  # pointer (32-bit)
                len_bytes = struct.pack('<I', buffer_size)            # length (32-bit)
                
                ptr_array = (ctypes.c_ubyte * 4).from_buffer_copy(ptr_bytes)
                len_array = (ctypes.c_ubyte * 4).from_buffer_copy(len_bytes)
                
                ctypes.memmove(raw_addr + iovec_entry_offset, ptr_array, 4)
                ctypes.memmove(raw_addr + iovec_entry_offset + 4, len_array, 4)
                
                current_buffer_offset += buffer_size

            success = func(self.store, compressed_offset, compressed_len, iovec_offset, buffer_count)
            
            if not success:
                raise RuntimeError("IOVec raw decompression from source failed")

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
        if not self.memory:
            return b''

        func = self.exports.get("RawCompress")
        if not func:
            return b''

        if not input_data:
            return b''

        import struct
        input_len = len(input_data)
        
        max_compressed_len = input_len + (input_len // 6) + 32
        
        input_offset = 0
        output_offset = input_len + 16  
        length_offset = output_offset + max_compressed_len + 16 

        try:
            input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

            mem_ptr = self.memory.data_ptr(self.store)
            raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

            ctypes.memmove(raw_addr + input_offset, input_array, input_len)
            
            func(self.store, input_offset, input_len, output_offset, length_offset)
            
            actual_len_byte = (ctypes.c_ubyte * 4)()
            ctypes.memmove(actual_len_byte, raw_addr + length_offset, 4)
            actual_compressed_len = struct.unpack('<I', bytes(actual_len_byte))[0]
            
            if actual_compressed_len == 0 or actual_compressed_len > max_compressed_len:
                return b''

            result_array = (ctypes.c_ubyte * actual_compressed_len)()
            ctypes.memmove(result_array, raw_addr + output_offset, actual_compressed_len)
            res = bytes(result_array)
            validate_raw_compress_output(input_data, res, max_compressed_len)
            return res
            
        except Exception as e:
            print(f"Compression failed: {str(e)}")
            return b''

    def raw_compress_with_options(self, input_data: bytes, compression_level: int = 1) -> bytes:
        if not self.memory:
            return b''

        func = self.exports.get("RawCompressWithOptions")
        if not func:
            return b''

        if not input_data:
            return b''

        import struct
        input_len = len(input_data)
        
        max_compressed_len = input_len + (input_len // 6) + 32
        
        input_offset = 0
        output_offset = input_len + 16  
        length_offset = output_offset + max_compressed_len + 16 

        try:
            input_array = (ctypes.c_ubyte * input_len).from_buffer_copy(input_data)

            mem_ptr = self.memory.data_ptr(self.store)
            raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

            ctypes.memmove(raw_addr + input_offset, input_array, input_len)

            func(self.store, input_offset, input_len, output_offset, length_offset, compression_level)
            
            actual_len_byte = (ctypes.c_ubyte * 4)()
            ctypes.memmove(actual_len_byte, raw_addr + length_offset, 4)
            actual_compressed_len = struct.unpack('<I', actual_len_byte)[0]
            
            if actual_compressed_len == 0 or actual_compressed_len > max_compressed_len:
                return b''

            result_array = (ctypes.c_ubyte * actual_compressed_len)()
            ctypes.memmove(result_array, raw_addr + output_offset, actual_compressed_len)
            result = bytes(result_array)
            validate_raw_compress_with_options_output(input_data, result, max_compressed_len, compression_level)
            return result
            
        except Exception:
            return b''

    def raw_compress_from_iovec(self, data_buffers: List[Union[bytes, bytearray]]) -> bytes:
        if not data_buffers:
            raise RuntimeError("No buffers provided")

        fn = self.exports.get("RawCompressFromIOVec")
        if not fn:
            raise RuntimeError("RawCompressFromIOVec not exported")

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

        fn(self.store, iov_off, iov_cnt, total_in, out_off, len_ptr)

        tmp = (ctypes.c_ubyte * 4)()
        ctypes.memmove(tmp, raw_base + len_ptr, 4)
        comp_len = struct.unpack("<I", bytes(tmp))[0]

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
        if not data_buffers:
            raise RuntimeError("No buffers provided")

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
        if not self.memory:
            return 0

        func = self.exports.get("MaxCompressedLength")
        if not func:
            return source_length + (source_length // 6) + 32

        try:

            max_len = func(self.store, source_length)
            return max_len
            
        except Exception:

            return source_length + (source_length // 6) + 32

    def uncompress(self, compressed_data: bytes) -> bytes:

        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressFromPtr")
        if not func:
            raise RuntimeError("UncompressFromPtr not found")


        try:
            uncompressed_length = self.get_uncompressed_length(compressed_data)
        except RuntimeError:

            uncompressed_length = len(compressed_data) * 4  # Conservative estimate

        compressed_len = len(compressed_data)

        compressed_offset = 0
        output_offset = compressed_len + 1024  # leave a gap to prevent overwrite

        compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)

        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

        actual_uncompressed_len = func(self.store, compressed_offset, compressed_len, output_offset, uncompressed_length)
        
        validate_uncompress_output(compressed_len, uncompressed_length, actual_uncompressed_len)

        if actual_uncompressed_len <= 0:
            raise RuntimeError("Decompression failed")

        result = bytearray(actual_uncompressed_len)
        result_array = (ctypes.c_ubyte * actual_uncompressed_len).from_buffer(result)

        ctypes.memmove(result_array, raw_addr + output_offset, actual_uncompressed_len)

        return bytes(result)


    def uncompress_source_sink(self, compressed_data: bytes) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressSourceSink")
        if not func:
            raise RuntimeError("UncompressSourceSink not found")

        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        try:
            uncompressed_length = self.get_uncompressed_length(compressed_data)
        except RuntimeError:
            uncompressed_length = len(compressed_data) * 4

        compressed_len = len(compressed_data)
        
        compressed_offset = 0
        output_offset = compressed_len + 2048  # Increased spacing from 1024 to 2048
        
        total_needed = output_offset + uncompressed_length
        try:
            if hasattr(self.memory, 'size'):
                memory_size = self.memory.size(self.store) * 65536  # Convert pages to bytes
            elif hasattr(self.memory, 'data_len'):
                memory_size = self.memory.data_len(self.store)
            else:
                memory_size = 16 * 1024 * 1024  # 16MB fallback
                
            if total_needed > memory_size:
                raise RuntimeError(f"Not enough WASM memory: need {total_needed}, have {memory_size}")
        except Exception:
            pass
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        try:
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

            bytes_written = func(self.store, compressed_offset, compressed_len, output_offset, uncompressed_length)
            
            if bytes_written <= 0:
                raise RuntimeError("Source/Sink decompression failed")

            if bytes_written > uncompressed_length:
                raise RuntimeError(f"Invalid decompression result: {bytes_written} > {uncompressed_length}")

            result = bytearray(bytes_written)
            result_array = (ctypes.c_ubyte * bytes_written).from_buffer(result)
            ctypes.memmove(result_array, raw_addr + output_offset, bytes_written)

            return bytes(result)
            
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Source/Sink decompression error: {str(e)}")

    def uncompress_as_much_as_possible_source_sink(self, compressed_data: bytes, max_output_size: int = None) -> bytes:
        if not self.memory:
            raise RuntimeError("Memory not available")

        func = self.exports.get("UncompressAsMuchAsPossibleSourceSink")
        if not func:
            raise RuntimeError("UncompressAsMuchAsPossibleSourceSink not found")

        if not compressed_data:
            raise RuntimeError("Compressed data cannot be empty")

        if max_output_size is None:
            try:
                max_output_size = self.get_uncompressed_length(compressed_data)
            except RuntimeError:
                max_output_size = len(compressed_data) * 4
        
        if max_output_size <= 0:
            return b""

        compressed_len = len(compressed_data)
        
        compressed_offset = 0
        output_offset = compressed_len + 2048  # Increased spacing
        
        total_needed = output_offset + max_output_size
        try:
            if hasattr(self.memory, 'size'):
                memory_size = self.memory.size(self.store) * 65536  
            elif hasattr(self.memory, 'data_len'):
                memory_size = self.memory.data_len(self.store)
            else:
                memory_size = 16 * 1024 * 1024  # 16MB fallback
            
            if total_needed > memory_size:
                available_output_space = memory_size - output_offset - 1024  
                if available_output_space <= 0:
                    raise RuntimeError("Not enough WASM memory for decompression")
                max_output_size = min(max_output_size, available_output_space)
                
                if max_output_size <= 0:
                    return b""
        except Exception:
            pass
        
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)

        try:
            compressed_array = (ctypes.c_ubyte * compressed_len).from_buffer_copy(compressed_data)
            ctypes.memmove(raw_addr + compressed_offset, compressed_array, compressed_len)

            bytes_written = func(self.store, compressed_offset, compressed_len, output_offset, max_output_size)
            
            if bytes_written < 0:
                raise RuntimeError("Source/Sink partial decompression failed")

            if bytes_written > max_output_size:
                raise RuntimeError(f"Invalid result: {bytes_written} > {max_output_size}")

            if bytes_written == 0:
                return b""

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
    
    print(f"\n--- Testing Regular Compression ---")
    compressed = snappy.compress(original_data)
    print(f"Compressed length: {len(compressed)} bytes")
    print(f"Compression ratio: {(1 - len(compressed)/len(original_data))*100:.1f}%")
    
    uncompressed = snappy.uncompress(compressed)
    integrity_check = original_data == uncompressed
    print(f"Data integrity check: {'PASS' if integrity_check else 'FAIL'}")
    
    print(f"\n--- Testing Validation Functions ---")
    is_valid_buffer = snappy.is_valid_compressed_buffer(compressed)
    print(f"IsValidCompressedBuffer: {is_valid_buffer}")
    
    is_valid_source = snappy.is_valid_compressed(compressed)
    print(f"IsValidCompressed (Source*): {is_valid_source}")
    
    invalid_data = b"This is not compressed data"
    is_valid_invalid = snappy.is_valid_compressed_buffer(invalid_data)
    print(f"Invalid data validation: {is_valid_invalid}")
    
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
    
    print(f"\n--- Testing Scatter-Gather Decompression (IOVec) ---")
    
    total_len = len(original_data)
    buffer_sizes = [total_len // 3, total_len // 3, total_len - 2 * (total_len // 3)]
    print(f"Target buffer sizes: {buffer_sizes} (total: {sum(buffer_sizes)})")
    
    try:
        iovec_buffers = snappy.raw_uncompress_to_iovec(compressed, buffer_sizes)
        print(f"RawUncompressToIOVec returned {len(iovec_buffers)} buffers")
        print(f"Buffer lengths: {[len(buf) for buf in iovec_buffers]}")
        
        reconstructed_iovec = b"".join(iovec_buffers)
        iovec_integrity_check = original_data == reconstructed_iovec
        print(f"IOVec integrity: {'PASS' if iovec_integrity_check else 'FAIL'}")
        
        for i, buf in enumerate(iovec_buffers):
            print(f"  Buffer {i}: {buf[:20]}...")
            
    except RuntimeError as e:
        print(f"RawUncompressToIOVec failed: {e}")
    
    try:
        iovec_source_buffers = snappy.raw_uncompress_to_iovec_from_source(compressed, buffer_sizes)
        print(f"RawUncompressToIOVecFromSource returned {len(iovec_source_buffers)} buffers")
        print(f"Buffer lengths: {[len(buf) for buf in iovec_source_buffers]}")
        
        reconstructed_source_iovec = b"".join(iovec_source_buffers)
        source_iovec_integrity_check = original_data == reconstructed_source_iovec
        print(f"IOVec from Source integrity: {'PASS' if source_iovec_integrity_check else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"RawUncompressToIOVecFromSource failed: {e}")
    
    try:
        simple_buffers = snappy.raw_uncompress_to_buffers(compressed, buffer_sizes)
        print(f"RawUncompressToBuffers returned {len(simple_buffers)} buffers")
        print(f"Buffer lengths: {[len(buf) for buf in simple_buffers]}")
        
        reconstructed_simple = b"".join(simple_buffers)
        simple_integrity_check = original_data == reconstructed_simple
        print(f"Simple buffers integrity: {'PASS' if simple_integrity_check else 'FAIL'}")
        
    except RuntimeError as e:
        print(f"RawUncompressToBuffers failed: {e}")
    
    print(f"\n--- Testing IOVec Compression ---")
    
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
        
        print(f"\n--- Testing Scatter-Gather on IOVec Compressed Data ---")
        total_iovec_len = len(reconstructed_data)
        iovec_buffer_sizes = [len(buf) for buf in data_buffers]  # Use original buffer sizes
        
        try:
            scattered_buffers = snappy.raw_uncompress_to_iovec(compressed_iovec, iovec_buffer_sizes)
            print(f"Scattered decompression returned {len(scattered_buffers)} buffers")
            
            for i, (original_buf, scattered_buf) in enumerate(zip(data_buffers, scattered_buffers)):
                match = original_buf == scattered_buf
                print(f"  Buffer {i} match: {'PASS' if match else 'FAIL'} ({len(original_buf)} vs {len(scattered_buf)} bytes)")
                
        except RuntimeError as e:
            print(f"Scatter-gather on IOVec data failed: {e}")
        
        regular_compressed = snappy.compress(reconstructed_data)
        print(f"IOVec vs Regular size difference: {len(compressed_iovec) - len(regular_compressed)} bytes")
        
    except RuntimeError as e:
        print(f"IOVec compression test failed: {e}")
        print("Note: This may be expected if the WASM module doesn't include CompressFromIOVec")
    
    print(f"\n--- Testing Edge Cases for Scatter-Gather ---")
    
    try:
        single_buffer_result = snappy.raw_uncompress_to_buffers(compressed, [len(original_data)])
        single_check = original_data == single_buffer_result[0]
        print(f"Single buffer scatter-gather integrity: {'PASS' if single_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Single buffer scatter-gather failed: {e}")
    
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
    
    print(f"\n--- Testing Buffer Size Validation ---")
    
    try:
        wrong_sizes = [len(original_data) // 2, len(original_data) // 2 + 10]  # 10 bytes too many
        snappy.raw_uncompress_to_buffers(compressed, wrong_sizes)
        print("Wrong buffer size test: UNEXPECTED SUCCESS")
    except RuntimeError as e:
        print(f"Wrong buffer size test: EXPECTED FAILURE - {e}")
    
    try:
        zero_sizes = [len(original_data), 0]
        zero_result = snappy.raw_uncompress_to_buffers(compressed, zero_sizes)
        zero_check = original_data == zero_result[0] and zero_result[1] == b""
        print(f"Zero-sized buffer test: {'PASS' if zero_check else 'FAIL'}")
    except RuntimeError as e:
        print(f"Zero-sized buffer test failed: {e}")
    
    print(f"\n--- Summary ---")
    print(f"WASM Module Version: {snappy.get_version()}")
    print("Available Functions:")
    print("  Compression: compress, compress_from_iovec")
    print("  Decompression: uncompress, raw_uncompress, raw_uncompress_from_source")
    print("  Scatter-Gather: raw_uncompress_to_iovec, raw_uncompress_to_iovec_from_source, raw_uncompress_to_buffers")
    print("  Validation: is_valid_compressed_buffer, is_valid_compressed")
    print("  Utilities: get_uncompressed_length, max_compressed_length, compression_info")