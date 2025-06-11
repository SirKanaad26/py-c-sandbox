# Update wasm_sandbox_framework/core/__init__.py

from .sandbox import WasmSandbox
from .types import Tainted
from .memory import WasmMemoryManager
from .function_wrapper import SandboxedFunction

__all__ = ['WasmSandbox', 'Tainted', 'WasmMemoryManager', 'SandboxedFunction']