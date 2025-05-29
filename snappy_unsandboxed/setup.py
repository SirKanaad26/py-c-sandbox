from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="cython_snappy",
    sources=[
        "py_c_connector.pyx",  # or .cpp if pure C++
        "snappy/snappy.cc",
        "snappy/snappy-sinksource.cc",
        "snappy/snappy-stubs-internal.cc"
    ],
    include_dirs=["snappy"],
    language="c++",
    extra_compile_args=["/std:c++14"],
)

setup(
    name="cython_snappy",
    ext_modules=cythonize([ext]),
)
