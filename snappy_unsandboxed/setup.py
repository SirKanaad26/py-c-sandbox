from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "cython_snappy",
        sources=["py_c_connector.pyx"],
        include_dirs=["snappy"],
        language="c++",  # Important!
    )
]

setup(
    name="cython_snappy",
    ext_modules=cythonize(ext_modules),
)
