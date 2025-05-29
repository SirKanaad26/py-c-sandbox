# snappy_wrapper.pyx
# Alternative Cython wrapper for Google's Snappy compression library

from libcpp cimport bool
from libcpp.string cimport string

# Use unsigned long instead of size_t to avoid import issues
ctypedef unsigned long size_t

# Declare the C++ functions from snappy
cdef extern from "snappy.h" namespace "snappy":
    size_t MaxCompressedLength(size_t source_bytes) nogil
    bool Compress(const char* input, size_t input_length, string* output) nogil
    bool Uncompress(const char* input, size_t input_length, string* output) nogil

def max_compressed_length(unsigned long source_bytes):
    """
    Calculate the maximum possible compressed length for given input size.
    
    Args:
        source_bytes (int): Size of the uncompressed data in bytes
        
    Returns:
        int: Maximum possible size of compressed data
    """
    cdef size_t result
    with nogil:
        result = MaxCompressedLength(source_bytes)
    return result

def compress_data(bytes input_data):
    """
    Compress data using Snappy compression.
    
    Args:
        input_data (bytes): Data to compress
        
    Returns:
        bytes: Compressed data
        
    Raises:
        RuntimeError: If compression fails
    """
    cdef const char* input_ptr = input_data
    cdef size_t input_length = len(input_data)
    cdef string output
    cdef bool success
    
    with nogil:
        success = Compress(input_ptr, input_length, &output)
    
    if not success:
        raise RuntimeError("Compression failed")
    
    return output

def uncompress_data(bytes compressed_data):
    """
    Uncompress Snappy-compressed data.
    
    Args:
        compressed_data (bytes): Compressed data
        
    Returns:
        bytes: Uncompressed data
        
    Raises:
        RuntimeError: If decompression fails
    """
    cdef const char* input_ptr = compressed_data
    cdef size_t input_length = len(compressed_data)
    cdef string output
    cdef bool success
    
    with nogil:
        success = Uncompress(input_ptr, input_length, &output)
    
    if not success:
        raise RuntimeError("Decompression failed")
    
    return output