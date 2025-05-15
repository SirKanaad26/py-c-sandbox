from wasmtime import Store, Module, Instance, Memory, MemoryType, Limits, Linker, WasiConfig
import ctypes

# 1. Setup store and WASI
store = Store()
wasi_config = WasiConfig()
store.set_wasi(wasi_config)

# 2. Create memory
mem_type = MemoryType(Limits(min=1, max=4))
memory = Memory(store, mem_type)

# 3. Load and compile the module
module = Module.from_file(store.engine, "capitalize.wasm")

# 4. Link imports including WASI
linker = Linker(store.engine)
linker.define(store, "env", "memory", memory)
linker.define_wasi()

# 5. Instantiate the module
instance = linker.instantiate(store, module)

# Step 5: Expose a callable function
def wasm_capitalize(input_str):
    capitalize = instance.exports(store)["capitalize"]
    mem = instance.exports(store)["memory"]

    ba = bytearray(input_str.encode())
    n = len(ba)
    offset = 0
    mem_view = mem.data_ptr(store)
    raw_addr = ctypes.addressof(ctypes.cast(mem_view, ctypes.POINTER(ctypes.c_ubyte)).contents)
    src_ptr = (ctypes.c_ubyte * n).from_buffer(ba)
    ctypes.memmove(raw_addr + offset, src_ptr, n)

    capitalize(store, offset)

    result = bytearray(n)
    dest_ptr = (ctypes.c_ubyte * n).from_buffer(result)
    ctypes.memmove(dest_ptr, raw_addr + offset, n)

    return result.decode()