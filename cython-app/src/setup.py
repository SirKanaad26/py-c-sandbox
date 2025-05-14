from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy  # <-- Needed for numpy.get_include()

ext_module = Extension(
    "hello_wrapper",
    sources=["hello_wrapper.pyx"],
    include_dirs=[".", numpy.get_include()]  # <-- Fix: Add NumPy headers
)

setup(
    name="hello_world_example",
    ext_modules=cythonize([ext_module])
)
