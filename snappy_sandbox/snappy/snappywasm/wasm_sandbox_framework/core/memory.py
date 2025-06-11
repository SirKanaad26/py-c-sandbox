import struct
from typing import Union, List
import ctypes
from .types import Tainted

class WasmMemoryManager:
    """Manages reading and writing to WASM memory."""
    
    def __init__(self, memory, store, sandbox):
        self.memory = memory
        self.store = store
        self.sandbox = sandbox
    
    def malloc(self, size: int) -> int:
        """Allocate memory in WASM (requires malloc export)."""
        # This would call the WASM malloc function
        # For now, returning a placeholder
        return 0
    
    def free(self, ptr: int):
        """Free memory in WASM (requires free export)."""
        pass
    
    def write_bytes(self, ptr: int, data: bytes):
        """Write bytes to WASM memory."""
        mem_data = self.memory.data_ptr(self.store)
        mem_size = self.memory.data_len(self.store)
        mem_view = (ctypes.c_ubyte * mem_size).from_address(
            ctypes.addressof(ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte)).contents)
        )
        for i, byte in enumerate(data):
            mem_view[ptr + i] = byte

    def read_bytes(self, ptr: int, size: int) -> 'Tainted[bytes]':
        """Read bytes from WASM memory - returns tainted data."""
        from .types import Tainted
        mem_data = self.memory.data_ptr(self.store)
        mem_size = self.memory.data_len(self.store)
        mem_view = (ctypes.c_ubyte * mem_size).from_address(
            ctypes.addressof(ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte)).contents)
        )
        return Tainted(bytes(mem_view[ptr:ptr + size]), self.sandbox)
    
    def write_u32(self, ptr: int, value: int):
        """Write 32-bit unsigned integer."""
        self.write_bytes(ptr, struct.pack('<I', value))
    
    def read_u32(self, ptr: int) -> 'Tainted[int]':
        """Read 32-bit unsigned integer - returns tainted data."""
        tainted_bytes = self.read_buffer(ptr, 4)
        value = struct.unpack('<I', tainted_bytes.raw)[0]
        return Tainted(value, self.sandbox)
    
    def write_string(self, ptr: int, string: str):
        """Write null-terminated string."""
        data = string.encode('utf-8') + b'\0'
        self.write_bytes(ptr, data)
    
    def read_string(self, ptr: int, max_len: int = 1024) -> 'Tainted[str]':
        """Read null-terminated string - returns tainted data."""
        from .types import Tainted
        mem_data = self.memory.data_ptr(self.store)
        mem_size = self.memory.data_len(self.store)
        mem_view = (ctypes.c_ubyte * mem_size).from_address(
            ctypes.addressof(ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte)).contents)
        )
        end = ptr
        while end < ptr + max_len and mem_view[end] != 0:
            end += 1
        return Tainted(bytes(mem_view[ptr:end]).decode('utf-8'), self.sandbox)
    
    def write_buffer(self, ptr: int, data: Union[bytes, bytearray]):
        """Write a buffer (bytes or bytearray) to WASM memory using ctypes for efficiency."""
        
        data_len = len(data)
        data_array = (ctypes.c_ubyte * data_len).from_buffer_copy(data)
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        ctypes.memmove(raw_addr + ptr, data_array, data_len)

    def read_buffer(self, ptr: int, size: int) -> 'Tainted[bytes]':
        """Read a buffer from WASM memory - returns tainted data."""
        result_bytes = bytearray(size)
        result_array = (ctypes.c_ubyte * size).from_buffer(result_bytes)
        mem_ptr = self.memory.data_ptr(self.store)
        raw_addr = ctypes.addressof(ctypes.cast(mem_ptr, ctypes.POINTER(ctypes.c_ubyte)).contents)
        ctypes.memmove(result_array, raw_addr + ptr, size)
        return Tainted(bytes(result_bytes), self.sandbox)