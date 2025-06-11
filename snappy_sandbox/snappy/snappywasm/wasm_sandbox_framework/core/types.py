from typing import TypeVar, Generic, Callable, Any, Union
from abc import ABC, abstractmethod

T = TypeVar('T')

class Tainted(Generic[T]):
    """
    Represents a tainted value from WASM that needs validation.
    Similar to RLBox's tainted types.
    """
    def __init__(self, value: T, sandbox: 'WasmSandbox'):
        self._value = value
        self._sandbox = sandbox
        self._validated = False
    
    def verify(self, validator: Callable[[T], T]) -> T:
        """Apply a validator function to untaint the value."""
        validated_value = validator(self._value)
        self._validated = True
        print(validated_value)
        return validated_value
    
    def copy_and_verify(self, validator: Callable[[T], T]) -> T:
        """Copy and verify the value (for complex types)."""
        return self.verify(validator)
    
    @property
    def raw(self) -> T:
        """Get raw value - use with caution!"""
        return self._value
