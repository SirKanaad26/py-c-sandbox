from typing import Any, Callable, Type, get_type_hints
from .types import Tainted

class SandboxedFunction:
    """Wraps a WASM function to return tainted values."""
    
    def __init__(self, func, sandbox: 'WasmSandbox', name: str):
        self.func = func
        self.sandbox = sandbox
        self.name = name
    
    def __call__(self, *args, **kwargs):
        """Call the WASM function and return tainted result."""
        # Convert arguments if needed
        converted_args = self._convert_args(args)
        
        # Call the actual WASM function
        result = self.func(self.sandbox.store, *converted_args)
        
        # Return tainted result
        return Tainted(result, self.sandbox)
    
    def _convert_args(self, args):
        """Convert Python arguments to WASM-compatible format."""
        # This is a simplified version - extend as needed
        return args