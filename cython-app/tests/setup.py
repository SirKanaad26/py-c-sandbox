from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy
import os

ext = Extension(
    name="hello_wrapper_test",
    sources=[
        "./hello_wrapper_test.pyx",
        "./evil_variants/copy_array_test.c"
    ],
    include_dirs=[
        "tests",
        "./evil_variants",
        numpy.get_include()
    ],
)

setup(
    name="mockable_wrapper",
    ext_modules=cythonize(
        [ext],
        build_dir="build_output",      # This controls where .c files are written
        language_level=3
    ),
    options={
        "build": {
            "build_base": "build_output"  # Where build/temp/... and .o files go
        }
    }
)
