# snappy_wrapper.pyx
# Cython wrapper for Google's Snappy compression library

from libcpp cimport bool
from libcpp.string cimport string
from libc.stddef cimport size_t
from libc.stdint cimport uint32_t

# Declare the C++ functions from snappy
cdef extern from "snappy.h" namespace "snappy":
    # CompressionOptions struct
    cdef cppclass CompressionOptions:
        int level
        CompressionOptions() nogil
        CompressionOptions(int compression_level) nogil
        @staticmethod
        int MinCompressionLevel()
        @staticmethod
        int MaxCompressionLevel()
        @staticmethod
        int DefaultCompressionLevel()
    
    # Core compression functions
    size_t MaxCompressedLength(size_t source_bytes) nogil
    size_t Compress(const char* input, size_t input_length, string* compressed) nogil
    size_t Compress(const char* input, size_t input_length, string* compressed, CompressionOptions options) nogil
    void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length) nogil
    void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length, CompressionOptions options) nogil
    bool GetUncompressedLength(const char* compressed, size_t compressed_length, size_t* result) nogil
    bool RawUncompress(const char* compressed, size_t compressed_length, char* uncompressed) nogil
    bool Uncompress(const char* compressed, size_t compressed_length, string* uncompressed) nogil
    bool IsValidCompressedBuffer(const char* compressed, size_t compressed_length) nogil

# Python wrapper class for CompressionOptions
cdef class PyCompressionOptions:
    cdef CompressionOptions opt
    
    def __cinit__(self, int level=1):
        if level < 1 or level > 2:
            raise ValueError("Compression level must be 1 or 2")
        self.opt = CompressionOptions(level)
    
    def get_level(self):
        return self.opt.level
    
    @staticmethod
    def min_level():
        return CompressionOptions.MinCompressionLevel()
    
    @staticmethod
    def max_level():
        return CompressionOptions.MaxCompressionLevel()
    
    @staticmethod
    def default_level():
        return CompressionOptions.DefaultCompressionLevel()

# Python wrapper functions
def max_compressed_length(size_t source_bytes):
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

def compress_data(bytes input_data, PyCompressionOptions options=None):
    """
    Compress data using Snappy compression.
    
    Args:
        input_data (bytes): Data to compress
        options (PyCompressionOptions, optional): Compression options
        
    Returns:
        bytes: Compressed data
        
    Raises:
        RuntimeError: If compression fails
    """
    cdef:
        const char* input_ptr = input_data
        size_t input_length = len(input_data)
        string output
        size_t compressed_length
    
    if options is None:
        with nogil:
            compressed_length = Compress(input_ptr, input_length, &output)
    else:
        with nogil:
            compressed_length = Compress(input_ptr, input_length, &output, options.opt)
    
    if compressed_length == 0:
        raise RuntimeError("Compression failed")
    
    return output

def compress_raw(bytes input_data, PyCompressionOptions options=None):
    """
    Compress data using Snappy raw compression.
    
    Args:
        input_data (bytes): Data to compress
        options (PyCompressionOptions, optional): Compression options
        
    Returns:
        bytes: Compressed data
    """
    cdef:
        const char* input_ptr = input_data
        size_t input_length = len(input_data)
        size_t max_output_length = MaxCompressedLength(input_length)
        bytes output_buffer = bytes(max_output_length)
        char* output_ptr = output_buffer
        size_t compressed_length = max_output_length
    
    if options is None:
        with nogil:
            RawCompress(input_ptr, input_length, output_ptr, &compressed_length)
    else:
        with nogil:
            RawCompress(input_ptr, input_length, output_ptr, &compressed_length, options.opt)
    
    return output_buffer[:compressed_length]

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
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        string output
        bool success
    
    with nogil:
        success = Uncompress(input_ptr, input_length, &output)
    
    if not success:
        raise RuntimeError("Decompression failed")
    
    return output

def uncompress_raw(bytes compressed_data):
    """
    Uncompress Snappy-compressed data using raw decompression.
    
    Args:
        compressed_data (bytes): Compressed data
        
    Returns:
        bytes: Uncompressed data
        
    Raises:
        RuntimeError: If decompression fails or unable to get uncompressed length
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        size_t uncompressed_length
        bool success
    
    # First get the uncompressed length
    with nogil:
        success = GetUncompressedLength(input_ptr, input_length, &uncompressed_length)
    
    if not success:
        raise RuntimeError("Unable to get uncompressed length")
    
    # Now decompress
    cdef:
        bytes output_buffer = bytes(uncompressed_length)
        char* output_ptr = output_buffer
    
    with nogil:
        success = RawUncompress(input_ptr, input_length, output_ptr)
    
    if not success:
        raise RuntimeError("Raw decompression failed")
    
    return output_buffer

def get_uncompressed_length(bytes compressed_data):
    """
    Get the uncompressed length from compressed data.
    
    Args:
        compressed_data (bytes): Compressed data
        
    Returns:
        int: Uncompressed data length
        
    Raises:
        RuntimeError: If unable to get length
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        size_t result
        bool success
    
    with nogil:
        success = GetUncompressedLength(input_ptr, input_length, &result)
    
    if not success:
        raise RuntimeError("Unable to get uncompressed length")
    
    return result

def is_valid_compressed_buffer(bytes compressed_data):
    """
    Check if the given data is a valid Snappy compressed buffer.
    
    Args:
        compressed_data (bytes): Data to check
        
    Returns:
        bool: True if valid Snappy compressed data, False otherwise
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        bool result
    
    with nogil:
        result = IsValidCompressedBuffer(input_ptr, input_length)
    
    return result