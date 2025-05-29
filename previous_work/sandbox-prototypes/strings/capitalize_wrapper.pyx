# cython: language_level=3
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../sandbox/src")))
from sandbox import CythonSandbox



wasm_path = os.path.join(os.path.dirname(__file__), "capitalize.wasm")
sandbox = CythonSandbox(wasm_path)
sandbox.create_sandbox()

def cy_capitalize(str input_str):
    tainted_result = sandbox.invoke_function("capitalize", input_str)
    return tainted_result.copy_and_verify(lambda s: s if s.isupper() else None)
