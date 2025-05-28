
import os
import struct
from wasmtime import Store, Module, Instance, Func
from .utils import create_wasm_imports
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
    
    def get_uncompressed_length(self, compressed_data: bytes) -> int:
        """Get uncompressed length from compressed data using raw memory copy via ctypes"""
        if not self.memory:
            raise RuntimeError("Memory not available - cannot use GetUncompressedLength")

        func = self.exports.get("GetUncompressedLengthFromPtr")
        if not func:
            raise RuntimeError("GetUncompressedLengthFromPtr not found")

        # Prepare offsets
        input_len = len(compressed_data)
        input_offset = 0
        result_offset = input_len + 1024  # leave room after the input

        # Copy compressed_data into WASM memory
        src_array = (ctypes.c_ubyte * input_len).from_buffer_copy(compressed_data)
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        ctypes.memmove(raw_addr + input_offset, src_array, input_len)

        # Call the WASM function
        success = func(self.store, input_offset, input_len, result_offset)
        if not success:
            raise ValueError("Failed to get uncompressed length - invalid compressed data")

        # Read back the 8-byte result
        result_buf = (ctypes.c_ubyte * 4)()
        ctypes.memmove(result_buf, raw_addr + result_offset, 4)
        return struct.unpack('<I', bytes(result_buf))[0]
