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
    
    for level in compression_info["supported_levels"]:
        print(f"\n--- Testing Compression Level {level} ---")
        
        compressed = snappy.compress(original_data, compression_level=level)
        print(f"Compressed length (level {level}): {len(compressed)} bytes")
        print(f"Compression ratio (level {level}): {(1 - len(compressed)/len(original_data))*100:.1f}%")
        
        is_valid = snappy.is_valid_compressed_buffer(compressed)
        print(f"Compressed data is valid: {is_valid}")
        
        expected_length = snappy.get_uncompressed_length(compressed)
        print(f"Expected uncompressed length: {expected_length} bytes")
        
        uncompressed = snappy.uncompress(compressed)
        print(f"Uncompressed length: {len(uncompressed)} bytes")
        
        integrity_check = original_data == uncompressed
        print(f"Data integrity check: {'PASS' if integrity_check else 'FAIL'}")
        
        if not integrity_check:
            print(f"Original:     {original_data[:100]}")
            print(f"Uncompressed: {uncompressed[:100]}")
    
    print(f"\n--- Testing Default Compression ---")
    compressed_default = snappy.compress(original_data)
    print(f"Default compressed length: {len(compressed_default)} bytes")
    print(f"Default compression ratio: {(1 - len(compressed_default)/len(original_data))*100:.1f}%")
    
    uncompressed_default = snappy.uncompress(compressed_default)
    default_check = original_data == uncompressed_default
    print(f"Default compression integrity: {'PASS' if default_check else 'FAIL'}")
