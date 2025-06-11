from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# Full dotted module name
ext_modules = [
    Extension(
        name="snappy_sandbox_framework",                # key: must match Python package name
        sources=["snappy_sandbox_framework.pyx"],       # path relative to project root
        extra_link_args=[
            "-Wl,-undefined,dynamic_lookup" if os.uname().sysname == "Darwin" else ""
        ],
    )
]

setup(
    name="snappy_sandbox",
    ext_modules=cythonize(
        ext_modules,
        compiler_directives={'language_level': 3},
        annotate=True
    ),
    # packages=["snappywasm"],
    zip_safe=False,
)


