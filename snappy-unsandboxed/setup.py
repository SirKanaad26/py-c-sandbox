# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
import os
import glob
import shutil

# Path to your local snappy directory
SNAPPY_DIR = "./snappy"

# Check if snappy directory exists
if not os.path.exists(SNAPPY_DIR):
    raise FileNotFoundError(f"Snappy directory not found at {SNAPPY_DIR}")

# Create config.h if it doesn't exist
config_h_path = os.path.join(SNAPPY_DIR, "config.h")
if not os.path.exists(config_h_path):
    # Check if config.h exists in the current directory
    if os.path.exists("config.h"):
        shutil.copy("config.h", config_h_path)
        print(f"Copied config.h to {config_h_path}")
    else:
        print("Warning: config.h not found. Please create it in the snappy directory.")
        print("You can use the provided config.h template.")

# Find all necessary snappy source files
snappy_sources = [
    os.path.join(SNAPPY_DIR, "snappy.cc"),
    os.path.join(SNAPPY_DIR, "snappy-sinksource.cc"),
    os.path.join(SNAPPY_DIR, "snappy-stubs-internal.cc"),
]

# Add snappy-c.cc only if it exists
snappy_c_path = os.path.join(SNAPPY_DIR, "snappy-c.cc")
if os.path.exists(snappy_c_path):
    snappy_sources.append(snappy_c_path)

# Define the extension with all snappy sources included
extensions = [
    Extension(
        "snappy_wrapper",
        ["snappy_wrapper.pyx"] + snappy_sources,  # Include all snappy sources
        include_dirs=[SNAPPY_DIR],
        language="c++",
        extra_compile_args=[
            "-std=c++11",
            "-O3",  # Optimization
            "-DNDEBUG",  # Release mode
            # Platform-specific flags
            "-fPIC" if os.name != 'nt' else "",
        ],
        extra_link_args=[
            "-Wl,-undefined,dynamic_lookup" if os.uname().sysname == "Darwin" else ""
        ],
        define_macros=[],  # Removed HAVE_CONFIG_H since we're creating the file
    )
]

setup(
    name="snappy_wrapper",
    ext_modules=cythonize(
        extensions, 
        compiler_directives={'language_level': 3},
        annotate=True  # Generates HTML annotations for optimization
    ),
    zip_safe=False,
)