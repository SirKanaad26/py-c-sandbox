# Snappy Cython Wrapper

A simple Cython wrapper for Google's Snappy compression library, starting with the `snappy_max_compressed_length` function.

## What This Does

This project demonstrates how to wrap a C library function using Cython. We're starting with the simplest function from Snappy's C API:

- `snappy_max_compressed_length()` - calculates the maximum possible size of compressed data

## Project Structure

```
├── snappy_wrapper.pyx    # Cython source code
├── setup.py             # Build configuration
├── main.py              # Test script
├── Makefile            # Build automation
└── README.md           # This file
```

## Prerequisites

### Install Snappy Library

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libsnappy-dev python3-dev
```

**macOS (with Homebrew):**
```bash
brew install snappy
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install snappy-devel python3-devel
```

### Install Python Dependencies

```bash
pip install cython setuptools
```

## Quick Start

1. **Build the extension:**
   ```bash
   make build
   # OR manually:
   python setup.py build_ext --inplace
   ```

2. **Run the test:**
   ```bash
   make test
   # OR manually:
   python main.py
   ```

3. **Clean up:**
   ```bash
   make clean
   ```

## Expected Output

When you run `python main.py`, you should see something like:

```
=== Snappy Max Compressed Length Test ===

Input size:        0 bytes
Max compressed:       32 bytes
Overhead:       32 bytes (0.0%)
----------------------------------------
Input size:       10 bytes
Max compressed:       76 bytes
Overhead:       66 bytes (660.0%)
----------------------------------------
Input size:      100 bytes
Max compressed:      244 bytes
Overhead:      144 bytes (144.0%)
----------------------------------------
Input size:     1000 bytes
Max compressed:     1324 bytes
Overhead:      324 bytes (32.4%)
----------------------------------------
Input size:    10000 bytes
Max compressed:    13240 bytes
Overhead:     3240 bytes (32.4%)
----------------------------------------
Input size:   100000 bytes
Max compressed:   132400 bytes
Overhead:    32400 bytes (32.4%)
----------------------------------------
Input size:  1000000 bytes
Max compressed:  1324000 bytes
Overhead:   324000 bytes (32.4%)
----------------------------------------

✅ Snappy wrapper working successfully!
🚀 You can now extend this to wrap compress/decompress functions!
```

## How It Works

1. **snappy_wrapper.pyx**: Declares the external C function and provides a Python wrapper
2. **setup.py**: Configures the build process and links against libsnappy
3. **main.py**: Tests the wrapper with various input sizes

## Next Steps

Once this simple function works, you can extend it to wrap more complex Snappy functions like:

- `snappy_compress()` - actual compression
- `snappy_uncompress()` - decompression
- `snappy_uncompressed_length()` - get uncompressed size
- `snappy_validate_compressed_buffer()` - validate compressed data

## Troubleshooting

**Error: `snappy-c.h: No such file or directory`**
- Make sure libsnappy-dev is installed
- You may need to add include paths to setup.py

**Error: `cannot find -lsnappy`**
- Make sure libsnappy is installed
- You may need to add library paths to setup.py

**Error: `ModuleNotFoundError: No module named 'snappy_wrapper'`**
- Make sure you've built the extension: `make build`
- Check that a `.so` file was created in your directory
