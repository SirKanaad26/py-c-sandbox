from setuptools import setup, Extension
from Cython.Build import cythonize
import os

ext_modules = [
    Extension(
        name="snappy_sandbox",               
        sources=["snappy_sandbox.pyx"],    
        extra_link_args=[
            "-Wl,-undefined,dynamic_lookup" if os.uname().sysname == "Darwin" else ""
        ],
    )
]

setup(
    name="smappy_sandbox",
    ext_modules=cythonize(
        ext_modules,
        compiler_directives={'language_level': 3},
        annotate=True
    ),
    zip_safe=False,
)


