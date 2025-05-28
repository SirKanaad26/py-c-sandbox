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
module = Module.from_file(store.engine, "../wasm/snappy.wasm")

# 4. Link imports including WASI
linker = Linker(store.engine)
linker.define(store, "env", "memory", memory)
linker.define_wasi()

# 5. Instantiate the module
instance = linker.instantiate(store, module)
print(instance.exports(store))
