# Build configuration for Snappy Cython wrapper

from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# Detect Homebrew paths for macOS
if os.path.exists("/opt/homebrew"):  # Apple Silicon Mac
    brew_prefix = "/opt/homebrew"
elif os.path.exists("/usr/local/Homebrew"):  # Intel Mac
    brew_prefix = "/usr/local"
else:
    brew_prefix = None

# Extension module configuration
if brew_prefix:
    # macOS with Homebrew
    snappy_extension = Extension(
        name="snappy_wrapper",
        sources=["snappy_wrapper.pyx"],
        libraries=["snappy"],
        library_dirs=[f"{brew_prefix}/lib"],
        include_dirs=[f"{brew_prefix}/include"]
    )
else:
    # Linux or other systems
    snappy_extension = Extension(
        name="snappy_wrapper",
        sources=["snappy_wrapper.pyx"],
        libraries=["snappy"]
    )

setup(
    name="snappy_wrapper",
    ext_modules=cythonize([snappy_extension]),
    zip_safe=False,
)