from wasmtime import Store, Module, Instance, Linker, WasiConfig, Memory
from tainted import Tainted
import ctypes

class CythonSandbox:
    def __init__(self, wasm_path):
        self.wasm_path = wasm_path
        self.store = None
        self.module = None
        self.instance = None
        self.memory = None
        self.linker = None

    def create_sandbox(self):
        print(f"[Sandbox] Loading WASM module: {self.wasm_path}")

        self.store = Store()
        self.linker = Linker(self.store.engine)

        # Enable WASI for basic I/O or args if needed
        wasi_config = WasiConfig()
        self.store.set_wasi(wasi_config)
        self.linker.define_wasi()

        self.module = Module.from_file(self.store.engine, self.wasm_path)
        self.instance = self.linker.instantiate(self.store, self.module)

        # Grab exported memory
        self.memory = self.instance.exports(self.store)["memory"]
        print("[Sandbox] Initialized")

    def destroy_sandbox(self):
        self.store = None
        self.module = None
        self.instance = None
        self.memory = None
        self.linker = None
        print("[Sandbox] Destroyed")

    def write_to_wasm_memory(self, data: bytes, offset: int):
        mem_view = self.memory.data_ptr(self.store)
        addr = ctypes.addressof(ctypes.cast(mem_view, ctypes.POINTER(ctypes.c_ubyte)).contents)
        ctypes.memmove(addr + offset, data, len(data))
        return offset

    def read_from_wasm_memory(self, offset: int, size: int) -> bytes:
        mem_view = self.memory.data_ptr(self.store)
        addr = ctypes.addressof(ctypes.cast(mem_view, ctypes.POINTER(ctypes.c_ubyte)).contents)
        buffer = (ctypes.c_ubyte * size)()
        ctypes.memmove(buffer, addr + offset, size)
        return bytes(buffer)

    def invoke_function(self, fn_name: str, *args, offset: int = 0):
        """
        General function to call a WASM-exported function with int, float, or str arguments.
        Copies strings to WASM memory
        Wraps the return value as Tainted without interpreting its type.
        """
        fn = self.instance.exports(self.store)[fn_name]

        wasm_args = []
        string_args = []
        current_offset = offset

        for arg in args:
            if isinstance(arg, (int, float)):
                wasm_args.append(arg)

            elif isinstance(arg, str):
                encoded = arg.encode()
                str_len = len(encoded)
                self.write_to_wasm_memory(encoded, current_offset)
                string_args.append((current_offset, str_len))
                wasm_args.append(current_offset)
                current_offset += str_len

            else:
                raise TypeError(f"Unsupported argument type: {type(arg)}")

        raw_result = fn(self.store, *wasm_args)

        if string_args:
            results = [
                self.read_from_wasm_memory(addr, size).decode()
                for addr, size in string_args
            ]
            return Tainted(results[0] if len(results) == 1 else results)

        return Tainted(raw_result)
