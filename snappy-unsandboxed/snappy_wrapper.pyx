# snappy_wrapper.pyx
# Alternative Cython wrapper for Google's Snappy compression library

from libcpp cimport bool
from libcpp.string cimport string

# Use unsigned long instead of size_t to avoid import issues
ctypedef unsigned long size_t

# Declare the C++ functions from snappy
cdef extern from "snappy.h" namespace "snappy":
    cdef cppclass CompressionOptions:
        CompressionOptions() nogil
        CompressionOptions(int level) nogil
        int level

    size_t MaxCompressedLength(size_t source_bytes) nogil
    bool Compress(const char* input, size_t input_length, string* output) nogil
    bool Compress(const char* input, size_t input_length, string* output, CompressionOptions options) nogil
    bool Uncompress(const char* input, size_t input_length, string* output) nogil


# Python-visible wrapper class
cdef class PyCompressionOptions:
    cdef CompressionOptions opt

    def __cinit__(self, int level=1):
        if level < 1 or level > 2:
            raise ValueError("Compression level must be 1 or 2")
        self.opt = CompressionOptions(level)

    def set_level(self, int level):
        if level < 1 or level > 2:
            raise ValueError("Compression level must be 1 or 2")
        self.opt.level = level

    def get_level(self):
        return self.opt.level



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

def cython_CompressWithCustomOptions(bytes input_data, PyCompressionOptions py_opt):
    """
    Compress data using Snappy with a custom compression level.
    """
    cdef const char* input_ptr = input_data
    cdef size_t input_length = len(input_data)
    cdef string output
    cdef CompressionOptions options = py_opt.opt
    cdef bool success

    with nogil:
        success = Compress(input_ptr, input_length, &output, options)

    if not success:
        raise RuntimeError("Compression failed with custom options")

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