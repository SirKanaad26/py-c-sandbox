# capitalize_wrapper.pyx
from libc.string cimport strcpy
cdef extern from "capitalize.h":
    void capitalize(char* str)

def py_capitalize(str input_str):
    cdef bytearray ba = bytearray(input_str, 'utf-8')  # Mutable byte buffer
    cdef char* c_str = ba  # Safe: bytearray memory is stable and writable
    capitalize(c_str)
    return ba.decode('utf-8')
