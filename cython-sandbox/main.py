# main.py
import hello_wrapper
import numpy as np

if __name__ == "__main__":
    print("Calling C memcpy from Python through Cython:")
    src = np.array([10, 20, 30, 40, 50], dtype=np.int32)
    print("Source:", src)

    dest = hello_wrapper.py_copy_array(src)
    print("Copied:", dest)

    payload = np.array([999999, 888888, 777777, 666666, 555555], dtype=np.int32)

    
    print("Corrupting stack variable through overflow...")
    new_secret = hello_wrapper.py_trigger_overflow(payload)
    print("Secret after overflow (should be corrupted):", new_secret)