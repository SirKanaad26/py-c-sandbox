
import os
import struct
from wasmtime import Store, Module, Instance, Func
from .utils import create_wasm_imports

class SnappyWasmDirect:
    def __init__(self, wasm_path="snappy.wasm"):
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
        input_ptr = 1024
        output_ptr = input_ptr + len(input_data) + 16

        memory_data = self.memory.data_ptr(self.store)
        memory_data[input_ptr:input_ptr + len(input_data)] = input_data

        compressed_len = func(self.store, input_ptr, len(input_data), output_ptr, max_out_len)
        if compressed_len == 0:
            raise RuntimeError("Compression failed")

        return bytes(memory_data[output_ptr:output_ptr + compressed_len])
