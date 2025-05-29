from wasmtime import Store, Module, Instance, Engine

# Load crash.wasm
engine = Engine()
store = Store(engine)
module = Module.from_file(store.engine, 'crash.wasm')
instance = Instance(store, module, [])

# Call exported function
try:
    unsafe_memcpy = instance.exports(store)["unsafe_memcpy"]
    result = unsafe_memcpy(store)
    print("[Python] unsafe_memcpy returned:", result)
except Exception as e:
    print("[Python] Caught WASM sandbox exception:", e)
