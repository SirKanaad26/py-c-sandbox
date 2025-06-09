# snappy_wrapper.pyx
# Cython wrapper for Google's Snappy compression library

from libcpp cimport bool
from libcpp.string cimport string
from libc.stddef cimport size_t
from libc.stdint cimport uint32_t
from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
from cpython.bytes cimport PyBytes_AsString

# For IOVec support
cdef extern from "<sys/uio.h>" nogil:
    cdef struct iovec:
        void* iov_base
        size_t iov_len

# Declare the C++ functions from snappy
cdef extern from "snappy.h" namespace "snappy":
    # Source and Sink interfaces (forward declarations)
    cdef cppclass Source:
        pass
    
    cdef cppclass Sink:
        pass
    
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
    
    # Constants
    int kBlockLog
    size_t kBlockSize
    int kMinHashTableBits
    size_t kMinHashTableSize
    int kMaxHashTableBits
    size_t kMaxHashTableSize
    
    # Core compression functions
    size_t MaxCompressedLength(size_t source_bytes) nogil
    
    # String-based compression
    size_t Compress(const char* input, size_t input_length, string* compressed) nogil
    size_t Compress(const char* input, size_t input_length, string* compressed, CompressionOptions options) nogil
    
    # IOVec-based compression
    size_t CompressFromIOVec(const iovec* iov, size_t iov_cnt, string* compressed) nogil
    size_t CompressFromIOVec(const iovec* iov, size_t iov_cnt, string* compressed, CompressionOptions options) nogil
    
    # Raw compression
    void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length) nogil
    void RawCompress(const char* input, size_t input_length, char* compressed, size_t* compressed_length, CompressionOptions options) nogil
    void RawCompressFromIOVec(const iovec* iov, size_t uncompressed_length, char* compressed, size_t* compressed_length) nogil
    void RawCompressFromIOVec(const iovec* iov, size_t uncompressed_length, char* compressed, size_t* compressed_length, CompressionOptions options) nogil
    
    # Decompression
    bool Uncompress(const char* compressed, size_t compressed_length, string* uncompressed) nogil
    bool RawUncompress(const char* compressed, size_t compressed_length, char* uncompressed) nogil
    bool RawUncompressToIOVec(const char* compressed, size_t compressed_length, const iovec* iov, size_t iov_cnt) nogil
    
    # Utility functions
    bool GetUncompressedLength(const char* compressed, size_t compressed_length, size_t* result) nogil
    bool IsValidCompressedBuffer(const char* compressed, size_t compressed_length) nogil
    
    # Source/Sink based operations
    size_t Compress(Source* reader, Sink* writer) nogil
    size_t Compress(Source* reader, Sink* writer, CompressionOptions options) nogil
    bool Uncompress(Source* compressed, Sink* uncompressed) nogil
    size_t UncompressAsMuchAsPossible(Source* compressed, Sink* uncompressed) nogil
    bool GetUncompressedLength(Source* source, uint32_t* result) nogil
    bool IsValidCompressed(Source* compressed) nogil
    bool RawUncompress(Source* compressed, char* uncompressed) nogil
    bool RawUncompressToIOVec(Source* compressed, const iovec* iov, size_t iov_cnt) nogil

# Custom Source implementation for bytes
cdef extern from *:
    """
    #include <string>
    #include "snappy.h"
    #include "snappy-sinksource.h"
    
    class BytesSource : public snappy::Source {
    private:
        const char* data_;
        size_t size_;
        size_t pos_;
        
    public:
        BytesSource(const char* data, size_t size) 
            : data_(data), size_(size), pos_(0) {}
        
        virtual ~BytesSource() {}
        
        virtual size_t Available() const override {
            return size_ - pos_;
        }
        
        virtual const char* Peek(size_t* len) override {
            *len = Available();
            return data_ + pos_;
        }
        
        virtual void Skip(size_t n) override {
            pos_ += n;
            if (pos_ > size_) pos_ = size_;
        }
    };
    
    class StringSink : public snappy::Sink {
    private:
        std::string* dest_;
        
    public:
        StringSink(std::string* dest) : dest_(dest) {}
        
        virtual ~StringSink() {}
        
        virtual void Append(const char* data, size_t n) override {
            dest_->append(data, n);
        }
        
        virtual char* GetAppendBuffer(size_t length, char* scratch) override {
            dest_->resize(dest_->size() + length);
            return &(*dest_)[dest_->size() - length];
        }
        
        virtual char* GetAppendBufferVariable(
            size_t min_size, size_t desired_size_hint, char* scratch,
            size_t scratch_size, size_t* allocated_size) override {
            *allocated_size = desired_size_hint;
            return GetAppendBuffer(desired_size_hint, scratch);
        }
        
        virtual void AppendAndTakeOwnership(
            char* data, size_t n,
            void (*deleter)(void*, const char*, size_t),
            void* deleter_arg) override {
            Append(data, n);
            (*deleter)(deleter_arg, data, n);
        }
    };
    """
    cdef cppclass BytesSource(Source):
        BytesSource(const char* data, size_t size) nogil
        
    cdef cppclass StringSink(Sink):
        StringSink(string* dest) nogil

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

def get_constants():
    """Get Snappy constants."""
    return {
        'kBlockLog': kBlockLog,
        'kBlockSize': kBlockSize,
        'kMinHashTableBits': kMinHashTableBits,
        'kMinHashTableSize': kMinHashTableSize,
        'kMaxHashTableBits': kMaxHashTableBits,
        'kMaxHashTableSize': kMaxHashTableSize,
    }

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

def is_valid_compressed_source(bytes compressed_data):
    """
    Check if the given data is valid Snappy compressed data using Source interface.
    
    Args:
        compressed_data (bytes): Data to check
        
    Returns:
        bool: True if valid Snappy compressed data, False otherwise
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        BytesSource* source
        bool result
    
    source = new BytesSource(input_ptr, input_length)
    try:
        with nogil:
            result = IsValidCompressed(source)
        return result
    finally:
        del source

def compress_source_to_sink(bytes input_data, PyCompressionOptions options=None):
    """
    Compress data using Source/Sink interfaces.
    
    Args:
        input_data (bytes): Data to compress
        options (PyCompressionOptions, optional): Compression options
        
    Returns:
        bytes: Compressed data
    """
    cdef:
        const char* input_ptr = input_data
        size_t input_length = len(input_data)
        BytesSource* source
        string output
        StringSink* sink
        size_t compressed_length
    
    source = new BytesSource(input_ptr, input_length)
    sink = new StringSink(&output)
    
    try:
        if options is None:
            with nogil:
                compressed_length = Compress(source, sink)
        else:
            with nogil:
                compressed_length = Compress(source, sink, options.opt)
        
        if compressed_length == 0:
            raise RuntimeError("Source/Sink compression failed")
        
        return output
    finally:
        del source
        del sink

def uncompress_source_to_sink(bytes compressed_data):
    """
    Decompress data using Source/Sink interfaces.
    
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
        BytesSource* source
        string output
        StringSink* sink
        bool success
    
    source = new BytesSource(input_ptr, input_length)
    sink = new StringSink(&output)
    
    try:
        with nogil:
            success = Uncompress(source, sink)
        
        if not success:
            raise RuntimeError("Source/Sink decompression failed")
        
        return output
    finally:
        del source
        del sink

def uncompress_as_much_as_possible(bytes compressed_data):
    """
    Decompress as much data as possible from potentially corrupted compressed data.
    
    Args:
        compressed_data (bytes): Compressed data (possibly corrupted)
        
    Returns:
        tuple: (decompressed_bytes, bytes_processed)
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        BytesSource* source
        string output
        StringSink* sink
        size_t bytes_processed
    
    source = new BytesSource(input_ptr, input_length)
    sink = new StringSink(&output)
    
    try:
        with nogil:
            bytes_processed = UncompressAsMuchAsPossible(source, sink)
        
        return (output, bytes_processed)
    finally:
        del source
        del sink

def get_uncompressed_length_from_source(bytes compressed_data):
    """
    Get uncompressed length using Source interface.
    
    Args:
        compressed_data (bytes): Compressed data
        
    Returns:
        int: Uncompressed length
        
    Raises:
        RuntimeError: If unable to get length
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        BytesSource* source
        uint32_t result
        bool success
    
    source = new BytesSource(input_ptr, input_length)
    try:
        with nogil:
            success = GetUncompressedLength(source, &result)
        
        if not success:
            raise RuntimeError("Unable to get uncompressed length from source")
        
        return result
    finally:
        del source

def raw_uncompress_from_source(bytes compressed_data):
    """
    Raw decompress using Source interface.
    
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
        BytesSource* source
        uint32_t uncompressed_length
        bytes output_buffer
        char* output_ptr
        bool success
    
    # First get the uncompressed length
    source = new BytesSource(input_ptr, input_length)
    try:
        with nogil:
            success = GetUncompressedLength(source, &uncompressed_length)
        
        if not success:
            raise RuntimeError("Unable to get uncompressed length")
    finally:
        del source
    
    # Now decompress
    source = new BytesSource(input_ptr, input_length)
    output_buffer = bytes(uncompressed_length)
    output_ptr = output_buffer
    
    try:
        with nogil:
            success = RawUncompress(source, output_ptr)
        
        if not success:
            raise RuntimeError("Raw decompression from source failed")
        
        return output_buffer
    finally:
        del source

def raw_uncompress_to_iovec_from_source(bytes compressed_data, list buffer_sizes):
    """
    Decompress to IOVec using Source interface.
    
    Args:
        compressed_data (bytes): Compressed data
        buffer_sizes (list of int): Buffer sizes for output
        
    Returns:
        list of bytes: Decompressed chunks
        
    Raises:
        RuntimeError: If decompression fails
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        BytesSource* source
        size_t iov_cnt = len(buffer_sizes)
        iovec* iov_array = <iovec*>malloc(sizeof(iovec) * iov_cnt)
        list output_bytes = []
        bool success
        size_t i
        char* buf_ptr
    
    if not iov_array:
        raise MemoryError("Failed to allocate IOVec array")
    
    source = new BytesSource(input_ptr, input_length)
    
    try:
        # Allocate buffers
        for i in range(iov_cnt):
            size = buffer_sizes[i]
            if size < 0:
                raise ValueError(f"Buffer size {i} must be non-negative")
            buf_ptr = <char*>malloc(size)
            if not buf_ptr:
                # Clean up previously allocated buffers
                for j in range(i):
                    free(iov_array[j].iov_base)
                raise MemoryError(f"Failed to allocate buffer {i}")
            iov_array[i].iov_base = <void*>buf_ptr
            iov_array[i].iov_len = size
        
        with nogil:
            success = RawUncompressToIOVec(source, iov_array, iov_cnt)
        
        if not success:
            # Clean up allocated buffers
            for i in range(iov_cnt):
                free(iov_array[i].iov_base)
            raise RuntimeError("IOVec decompression from source failed")
        
        # Copy data to Python bytes objects
        for i in range(iov_cnt):
            output_bytes.append((<char*>iov_array[i].iov_base)[:iov_array[i].iov_len])
            free(iov_array[i].iov_base)
        
        return output_bytes
    finally:
        del source
        free(iov_array)

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

def compress_from_iovec(list data_chunks, PyCompressionOptions options=None):
    """
    Compress data from multiple chunks using IOVec.
    
    Args:
        data_chunks (list of bytes): List of data chunks to compress
        options (PyCompressionOptions, optional): Compression options
        
    Returns:
        bytes: Compressed data
        
    Raises:
        RuntimeError: If compression fails
    """
    cdef:
        size_t iov_cnt = len(data_chunks)
        iovec* iov_array = <iovec*>malloc(sizeof(iovec) * iov_cnt)
        string output
        size_t compressed_length
        size_t i
    
    if not iov_array:
        raise MemoryError("Failed to allocate IOVec array")
    
    try:
        # Populate IOVec array
        for i in range(iov_cnt):
            chunk = data_chunks[i]
            if not isinstance(chunk, bytes):
                raise TypeError(f"Chunk {i} must be bytes, got {type(chunk)}")
            iov_array[i].iov_base = <void*>PyBytes_AsString(chunk)
            iov_array[i].iov_len = len(chunk)
        
        if options is None:
            with nogil:
                compressed_length = CompressFromIOVec(iov_array, iov_cnt, &output)
        else:
            with nogil:
                compressed_length = CompressFromIOVec(iov_array, iov_cnt, &output, options.opt)
        
        if compressed_length == 0:
            raise RuntimeError("IOVec compression failed")
        
        return output
    finally:
        free(iov_array)

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

def compress_raw_from_iovec(list data_chunks, PyCompressionOptions options=None):
    """
    Compress data from multiple chunks using raw IOVec compression.
    
    Args:
        data_chunks (list of bytes): List of data chunks to compress
        options (PyCompressionOptions, optional): Compression options
        
    Returns:
        bytes: Compressed data
    """
    cdef:
        size_t iov_cnt = len(data_chunks)
        iovec* iov_array = <iovec*>malloc(sizeof(iovec) * iov_cnt)
        size_t total_length = 0
        size_t max_output_length
        bytes output_buffer
        char* output_ptr
        size_t compressed_length
        size_t i
    
    if not iov_array:
        raise MemoryError("Failed to allocate IOVec array")
    
    try:
        # Populate IOVec array and calculate total length
        for i in range(iov_cnt):
            chunk = data_chunks[i]
            if not isinstance(chunk, bytes):
                raise TypeError(f"Chunk {i} must be bytes, got {type(chunk)}")
            iov_array[i].iov_base = <void*>PyBytes_AsString(chunk)
            iov_array[i].iov_len = len(chunk)
            total_length += len(chunk)
        
        max_output_length = MaxCompressedLength(total_length)
        output_buffer = bytes(max_output_length)
        output_ptr = output_buffer
        compressed_length = max_output_length
        
        if options is None:
            with nogil:
                RawCompressFromIOVec(iov_array, total_length, output_ptr, &compressed_length)
        else:
            with nogil:
                RawCompressFromIOVec(iov_array, total_length, output_ptr, &compressed_length, options.opt)
        
        return output_buffer[:compressed_length]
    finally:
        free(iov_array)

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

def uncompress_to_iovec(bytes compressed_data, list buffer_sizes):
    """
    Uncompress Snappy-compressed data into multiple buffers using IOVec.
    
    Args:
        compressed_data (bytes): Compressed data
        buffer_sizes (list of int): List of buffer sizes for output
        
    Returns:
        list of bytes: List of decompressed data chunks
        
    Raises:
        RuntimeError: If decompression fails
    """
    cdef:
        const char* input_ptr = compressed_data
        size_t input_length = len(compressed_data)
        size_t iov_cnt = len(buffer_sizes)
        iovec* iov_array = <iovec*>malloc(sizeof(iovec) * iov_cnt)
        list output_buffers = []
        list output_bytes = []
        bool success
        size_t i
        char* buf_ptr
    
    if not iov_array:
        raise MemoryError("Failed to allocate IOVec array")
    
    try:
        # Create output buffers and populate IOVec array
        for i in range(iov_cnt):
            size = buffer_sizes[i]
            if size < 0:
                raise ValueError(f"Buffer size {i} must be non-negative")
            # Create bytes buffer instead of bytearray
            buf = bytes(size)
            output_buffers.append(buf)
            # Allocate new memory for mutable buffer
            buf_ptr = <char*>malloc(size)
            if not buf_ptr:
                # Clean up previously allocated buffers
                for j in range(i):
                    free(iov_array[j].iov_base)
                raise MemoryError(f"Failed to allocate buffer {i}")
            iov_array[i].iov_base = <void*>buf_ptr
            iov_array[i].iov_len = size
        
        with nogil:
            success = RawUncompressToIOVec(input_ptr, input_length, iov_array, iov_cnt)
        
        if not success:
            # Clean up allocated buffers
            for i in range(iov_cnt):
                free(iov_array[i].iov_base)
            raise RuntimeError("IOVec decompression failed")
        
        # Copy data from allocated buffers to Python bytes objects
        for i in range(iov_cnt):
            output_bytes.append((<char*>iov_array[i].iov_base)[:iov_array[i].iov_len])
            free(iov_array[i].iov_base)
        
        return output_bytes
    finally:
        free(iov_array)

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