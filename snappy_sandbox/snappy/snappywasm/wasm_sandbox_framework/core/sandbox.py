import os
from wasmtime import Store, Module, Instance, Func
from typing import Dict, Any, Optional, Callable
from .memory import WasmMemoryManager
from .function_wrapper import SandboxedFunction
from .types import Tainted

class WasmSandbox:
    """Main sandbox class for isolating WASM modules."""
    
    def __init__(self, wasm_path: str, imports_factory: Optional[Callable] = None):
        self.wasm_path = wasm_path
        self.store = Store()
        self.instance = None
        self.exports = None
        self.memory_manager = None
        self._wrapped_functions: Dict[str, SandboxedFunction] = {}
        
        # Load and instantiate the WASM module
        self._load_module(imports_factory)
    
    def _load_module(self, imports_factory: Optional[Callable] = None):
        """Load and instantiate the WASM module."""
        with open(self.wasm_path, 'rb') as f:
            wasm_bytes = f.read()
        
        module = Module(self.store.engine, wasm_bytes)
        imports_needed = module.imports
        
        if len(imports_needed) > 0 and imports_factory:
            imports = imports_factory(self.store)
            import_list = self._resolve_imports(imports_needed, imports)
            self.instance = Instance(self.store, module, import_list)
        else:
            # Create dummy imports if needed
            import_list = []
            for imp in imports_needed:
                dummy = Func(self.store, imp.type, 
                           lambda *args: 0 if len(imp.type.results) > 0 else None)
                import_list.append(dummy)
            self.instance = Instance(self.store, module, import_list)
        
        self.exports = self.instance.exports(self.store)
        
        # Initialize memory manager if memory is exported
        memory = self.exports.get("memory", None)
        if memory:
            self.memory_manager = WasmMemoryManager(memory, self.store, self)
    
    def _resolve_imports(self, imports_needed, imports):
        """Resolve required imports."""
        import_list = []
        for imp in imports_needed:
            if imp.module in imports and imp.name in imports[imp.module]:
                import_list.append(imports[imp.module][imp.name])
            else:
                # Create dummy function
                dummy = Func(self.store, imp.type, 
                           lambda *args: 0 if len(imp.type.results) > 0 else None)
                import_list.append(dummy)
        return import_list
    
    def invoke_sandbox_function(self, func_name: str, *args) -> Tainted:
        """
        Invoke a sandboxed function and return a tainted result.
        This is the main interface for calling WASM functions.
        """
        if func_name not in self._wrapped_functions:
            func = self.exports.get(func_name)
            if not func:
                raise RuntimeError(f"Function '{func_name}' not found in exports")
            self._wrapped_functions[func_name] = SandboxedFunction(func, self, func_name)
        
        return self._wrapped_functions[func_name](*args)
    
    def get_memory_manager(self) -> WasmMemoryManager:
        """Get the memory manager for direct memory operations."""
        if not self.memory_manager:
            raise RuntimeError("No memory export found in WASM module")
        return self.memory_manager