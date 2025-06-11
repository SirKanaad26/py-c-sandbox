from typing import TypeVar, Callable, Any
from abc import ABC, abstractmethod

T = TypeVar('T')
def hello():
    print('hello')

class Validator(ABC):
    """Base class for validators."""
    
    @abstractmethod
    def validate(self, value: T) -> T:
        """Validate and return the untainted value."""
        pass

class RangeValidator(Validator):
    """Validates numeric values are within a range."""
    
    def __init__(self, min_val: float = None, max_val: float = None):
        self.min_val = min_val
        self.max_val = max_val
    
    def validate(self, value: float) -> float:
        if self.min_val is not None and value < self.min_val:
            raise ValueError(f"Value {value} is below minimum {self.min_val}")
        if self.max_val is not None and value > self.max_val:
            raise ValueError(f"Value {value} is above maximum {self.max_val}")
        return value

class LengthValidator(Validator):
    """Validates lengths/sizes."""
    
    def __init__(self, max_length: int):
        self.max_length = max_length
    
    def validate(self, value: int) -> int:
        if value < 0:
            raise ValueError(f"Length cannot be negative: {value}")
        if value > self.max_length:
            raise ValueError(f"Length {value} exceeds maximum {self.max_length}")
        return value