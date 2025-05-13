# main.py
import hello_wrapper
import numpy as np

if __name__ == "__main__":
    print("Calling C memcpy from Python through Cython:")
    src = np.array([10, 20, 30, 40, 50], dtype=np.int32)
    print("Source:", src)

    dest = hello_wrapper.py_copy_array(src)
    print("Copied:", dest)
