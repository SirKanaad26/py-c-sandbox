
from wasmtime import Store, Func, FuncType, ValType

def create_wasm_imports(store):
    def dummy_func(*args):
        return 0

    def abort_func():
        raise RuntimeError("WASM module called abort()")

    env_imports = {
        "abort": Func(store, FuncType([], []), abort_func),
        "__assert_fail": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32(), ValType.i32()], []), lambda *args: None),
        "__cxa_throw": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32()], []), lambda *args: None),
        "emscripten_memcpy_big": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32()], [ValType.i32()]), dummy_func),
        "emscripten_resize_heap": Func(store, FuncType([ValType.i32()], [ValType.i32()]), dummy_func),
    }

    return {"env": env_imports}
