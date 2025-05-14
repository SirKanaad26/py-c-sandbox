# cython: language_level=3
import numpy as np
cimport numpy as np

cdef extern from "evil_variants/copy_array_test.h":
    void copy_array_overflow(int* dest, int* src, int len)
    void copy_array_uaf(int* dest, int* src, int len)

cdef class CopyArray:
    cpdef np.ndarray[np.int32_t, ndim=1] call_overflow(self, np.ndarray[np.int32_t, ndim=1] src):
        cdef int n = src.shape[0]
        cdef np.ndarray[np.int32_t, ndim=1] dest = np.zeros(n, dtype=np.int32)
        copy_array_overflow(<int*> dest.data, <int*> src.data, n)
        return dest

    cpdef np.ndarray[np.int32_t, ndim=1] call_uaf(self, np.ndarray[np.int32_t, ndim=1] src):
        cdef int n = src.shape[0]
        cdef np.ndarray[np.int32_t, ndim=1] dest = np.zeros(n, dtype=np.int32)
        copy_array_uaf(<int*> dest.data, <int*> src.data, n)
        return dest
