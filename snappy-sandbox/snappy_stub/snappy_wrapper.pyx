# snappy_wrapper.pyx
# Cython wrapper for Google Snappy compression library

# External C function declarations
cdef extern from "snappy-c.h":
    # Simple function that calculates max compressed length
    size_t snappy_max_compressed_length(size_t source_length)

# Python wrapper function
def py_max_compressed_length(source_length: int) -> int:
    """
    Calculate the maximum possible size of compressed data.
    
    Args:
        source_length: The size of the input data in bytes
        
    Returns:
        The maximum possible size of the compressed data in bytes
        
    Example:
        >>> max_size = py_max_compressed_length(1000)
        >>> print(f"1000 bytes could compress to at most {max_size} bytes")
    """
    cdef size_t result = snappy_max_compressed_length(source_length)
    return result