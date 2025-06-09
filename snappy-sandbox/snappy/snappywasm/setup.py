from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# Full dotted module name
ext_modules = [
    Extension(
        name="snappywasm.core",                # key: must match Python package name
        sources=["snappywasm/core.pyx"],       # path relative to project root
    )
]

setup(
    name="snappywasm",
    ext_modules=cythonize(ext_modules, language_level=3),
    packages=["snappywasm"],
    zip_safe=False,
)


