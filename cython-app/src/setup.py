from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="capitalize_wrapper",
    # sources=["capitalize_wrapper.pyx", "capitalize.c"],  # Do NOT include .h here
    sources=["wasm_capitalize_wrapper.pyx", "capitalize.c"],  # Do NOT include .h here
    include_dirs=["."],  # The .h file should be in this directory
    language="c",
)

setup(
    ext_modules=cythonize([ext])
)
