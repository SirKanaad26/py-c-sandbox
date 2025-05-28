# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# Path to your local snappy directory
SNAPPY_DIR = "./snappy"

# Check if snappy directory exists
if not os.path.exists(SNAPPY_DIR):
    raise FileNotFoundError(f"Snappy directory not found at {SNAPPY_DIR}")

# Define the extension with local snappy build
extensions = [
    Extension(
        "snappy_wrapper",
        ["snappy_wrapper.pyx"],
        include_dirs=[SNAPPY_DIR],  # Include snappy headers
        library_dirs=[os.path.join(SNAPPY_DIR, "build")],  # Look for built library
        libraries=["snappy"],
        language="c++",
        extra_compile_args=["-std=c++11"],
        extra_link_args=[],
    )
]

setup(
    name="snappy_wrapper",
    ext_modules=cythonize(extensions, compiler_directives={'language_level': 3}),
    zip_safe=False,
)