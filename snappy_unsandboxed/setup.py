from setuptools import setup, Extension
from Cython.Build import cythonize
import glob

snappy_sources = glob.glob("snappy/*.cc")  # all snappy source files

ext_modules = [
    Extension(
        "cython_snappy",
        sources=["py_c_connector.pyx"] + snappy_sources + ["snappy_wrapper.cc"],
        include_dirs=["snappy"],
        language="c++",
        extra_compile_args=["/std:c++14"],  # or whatever C++ std you need
    )
]

setup(
    name="snappy",
    ext_modules=cythonize(ext_modules),
)
