cdef extern from "snappy/snappy_wrapper.h":
    size_t cython_MaxCompressedLength(size_t source_bytes)

cdef class CythonClass:
    def max_compressed_length(self, source_bytes):
        return cython_MaxCompressedLength(source_bytes)
