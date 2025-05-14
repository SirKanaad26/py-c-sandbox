# hello_wrapper.pyx

# Import Python-level NumPy for array creation
import numpy as np

# C-level import of NumPy
cimport numpy as cnp
from libc.stdlib cimport malloc, free
from libc.string cimport memcpy

# Ensure NumPy C API is initialized
cnp.import_array()

# Define the data type for our arrays (int32)
ctypedef cnp.int32_t DTYPE_t

# Declare the C function
cdef extern from "hello.h":
    void copy_array(int* dest, int* src, int len)

# Python-visible wrapper
def py_copy_array(cnp.ndarray[DTYPE_t, ndim=1] src not None):
    cdef int n = src.shape[0]
    cdef cnp.ndarray[DTYPE_t, ndim=1] dest = np.empty(n, dtype=np.int32)

    # Use PyData pointer access for raw C interop
    copy_array(<int*>cnp.PyArray_DATA(dest), <int*>cnp.PyArray_DATA(src), n)

    return dest
