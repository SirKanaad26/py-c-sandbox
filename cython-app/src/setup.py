# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="capitalize_wrapper",
    sources=["capitalize_wrapper.pyx", "capitalize.c"],
    include_dirs=["."],
    language="c",
)

setup(
    ext_modules=cythonize([ext])
)
