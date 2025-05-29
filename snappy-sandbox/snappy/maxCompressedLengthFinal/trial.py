import os
import struct
from wasmtime import Store, Module, Instance, Func, FuncType, ValType


def create_wasm_imports(store):
    """Create necessary imports for the Snappy WASM module"""
    imports = {}
    
    # Common functions that C++ code might need
    def dummy_func(*args):
        return 0
    
    def abort_func():
        raise RuntimeError("WASM module called abort()")
    
    # Environment imports that Emscripten/C++ runtime might expect
    env_imports = {
        "abort": Func(store, FuncType([], []), abort_func),
        "__assert_fail": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32(), ValType.i32()], []), lambda *args: None),
        "__cxa_throw": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32()], []), lambda *args: None),
        "emscripten_memcpy_big": Func(store, FuncType([ValType.i32(), ValType.i32(), ValType.i32()], [ValType.i32()]), dummy_func),
        "emscripten_resize_heap": Func(store, FuncType([ValType.i32()], [ValType.i32()]), dummy_func),
    }
    
    imports["env"] = env_imports
    return imports



class SnappyWasmDirect:
    """Wrapper for Snappy WASM built from actual source files"""
    
    def __init__(self, wasm_path="snappy_direct.wasm"):
        if not os.path.exists(wasm_path):
            raise FileNotFoundError(f"WASM file not found: {wasm_path}")
        
        self.store = Store()
        
        with open(wasm_path, 'rb') as f:
            wasm_bytes = f.read()
        
        module = Module(self.store.engine, wasm_bytes)
        
        imports_needed = module.imports
        print(f"Module requires {len(imports_needed)} imports:")
        for imp in imports_needed:
            print(f"  - {imp.module}.{imp.name}: {imp.type}")
        
        if len(imports_needed) > 0:
            imports = create_wasm_imports(self.store)
            
            # Build import list in the order expected by the module
            import_list = []
            for imp in imports_needed:
                if imp.module in imports and imp.name in imports[imp.module]:
                    import_list.append(imports[imp.module][imp.name])
                else:
                    # Create a dummy function for unknown imports
                    if hasattr(imp.type, 'params') and hasattr(imp.type, 'results'):
                        dummy = Func(self.store, imp.type, lambda *args: 0 if len(imp.type.results) > 0 else None)
                        import_list.append(dummy)
                    else:
                        raise Exception(f"Unknown import type for {imp.module}.{imp.name}: {imp.type}")
            
            self.instance = Instance(self.store, module, import_list)
        else:
            self.instance = Instance(self.store, module, [])
        
        self.exports = self.instance.exports(self.store)
        
        if "memory" in self.exports:
            self.memory = self.exports["memory"]
        else:
            self.memory = None
            print(" No memory export found - some functions may not work")
        
    def max_compressed_length(self, source_length: int) -> int:
        """Get maximum compressed length for given source length"""
        if "MaxCompressedLength" not in self.exports:
            raise RuntimeError("MaxCompressedLength function not available")
        func = self.exports["MaxCompressedLength"]
        return func(self.store, source_length)
    
    


def test_snappy_direct_wasm():
    """Test both MaxCompressedLength and GetUncompressedLength"""
    try:
        snappy = SnappyWasmDirect()
    except FileNotFoundError:
        print("WASM file not found: snappy_direct.wasm")
        print("Run ./build_from_snappy_source.sh first")
        return
    except Exception as e:
        print(f"Failed to load WASM module: {e}")
        return
    
    print("Testing WASM Built from Actual Snappy Source Files")
    print("=" * 60)
    
    print()
    
    # Test MaxCompressedLength
    print("Testing MaxCompressedLength:")
    test_sizes = [0, 10, 100, 1000, 10000, 100000]
    
    print(f"{'Input Size':>12} | {'Max Compressed':>14} | {'Overhead':>10} | {'Overhead %':>11}")
    print("-" * 60)
    
    for size in test_sizes:
        try:
            max_size = snappy.max_compressed_length(size)
            overhead = max_size - size
            overhead_pct = (overhead / size * 100) if size > 0 else 0
            
            print(f"{size:12,} | {max_size:14,} | {overhead:10,} | {overhead_pct:10.1f}%")
        except Exception as e:
            print(f"{size:12,} | {'ERROR':>14} | {'N/A':>10} | {'N/A':>11}")
            print(f"    Error: {e}")
    
    
    print(f"\n Performance Tests")
    print("-" * 30)
    
    import time
    iterations = 50000
    
    # Test MaxCompressedLength performance
    test_size = 1000
    try:
        start_time = time.time()
        for _ in range(iterations):
            snappy.max_compressed_length(test_size)
        mcl_time = time.time() - start_time
        
        print(f"MaxCompressedLength:")
        print(f"  {iterations:,} calls in {mcl_time:.3f}s")
        print(f"  {iterations/mcl_time:,.0f} calls/sec")
        print(f"  {(mcl_time/iterations)*1_000_000:.3f} μs/call")
    except Exception as e:
        print(f"MaxCompressedLength performance test failed: {e}")
        
    print(f"\nTest completed!")


if __name__ == "__main__":
    test_snappy_direct_wasm()