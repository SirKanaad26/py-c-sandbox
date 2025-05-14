# Hello World: C + Cython + Python Integration


## Overview

The project in `cpython-sandbox/` project demonstrates the integration chain:
```
Python (main.py) → Cython (hello_wrapper.pyx) → C (hello.h)
```
## Prerequisites

- Python 3.x
- pip (Python package manager)
- C compiler (gcc on Linux/macOS, MSVC on Windows)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install required Python packages:
   ```bash
   pip install cython setuptools
   ```

## Building

Build the Cython extension module:

```bash
python setup.py build_ext --inplace
```

This will generate:
- `hello_wrapper.c` - C code generated from the .pyx file
- `hello_wrapper.so` (Linux) / `hello_wrapper.pyd` (Windows) / `hello_wrapper.dylib` (macOS) - Compiled extension module

## Running

After building, run the main Python script:

```bash
python main.py
```

Expected output:
```
Calling C function from Python through Cython:
Hello, World from C!
Done!
```

## How It Works

1. **hello.h**: Contains a simple C function `hello_world()` that prints a message
2. **hello_wrapper.pyx**: Cython file that:
   - Declares the C function using `cdef extern`
   - Provides a Python-callable wrapper `py_hello_world()`
3. **setup.py**: Configures the build process using setuptools
4. **main.py**: Imports the compiled module and calls the wrapped function

## File Descriptions

### hello.h
A simple C header file with an inline function.

### hello_wrapper.pyx
Cython code that exposes the C function to Python.

### main.py
Python code that uses the wrapped C function.

## Troubleshooting

### "Cython.Build not found" Error
Make sure Cython is properly installed:
```bash
pip install --upgrade cython
python -c "from Cython.Build import cythonize"
```

### Compilation Errors
Ensure you have a C compiler installed:
- **Linux**: `sudo apt-get install build-essential`
- **macOS**: `xcode-select --install`
- **Windows**: Install Visual Studio Build Tools

### Module Import Error
Make sure you've built the extension before running:
```bash
python setup.py build_ext --inplace
```

## Clean Build

To clean build artifacts:
```bash
rm -rf build/
rm -f *.so *.pyd *.dylib
rm -f hello_wrapper.c
```

## Development

The `.gitignore` file is configured to exclude compiled files and build artifacts. When contributing, ensure you don't commit:
- `*.so`, `*.pyd`, `*.dylib` files
- `build/` directory
- `__pycache__/` directory
- Generated C files (optional)

## License

[Your chosen license]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Resources

- [Cython Documentation](https://cython.readthedocs.io/)
- [Python C API](https://docs.python.org/3/c-api/)
- [Setuptools Documentation](https://setuptools.pypa.io/)