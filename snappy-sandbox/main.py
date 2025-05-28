#!/usr/bin/env python3
# main.py
# Test script for Snappy wrapper

from snappy_wrapper import py_max_compressed_length

def main():
    """Test the Snappy max compressed length function."""
    
    print("=== Snappy Max Compressed Length Test ===")
    print()
    
    # Test various input sizes
    test_sizes = [0, 10, 100, 1000, 10000, 100000, 1000000]
    
    for size in test_sizes:
        max_compressed = py_max_compressed_length(size)
        overhead_bytes = max_compressed - size
        overhead_percent = (overhead_bytes / size * 100) if size > 0 else 0
        
        print(f"Input size: {size:>8} bytes")
        print(f"Max compressed: {max_compressed:>8} bytes")
        print(f"Overhead: {overhead_bytes:>8} bytes ({overhead_percent:.1f}%)")
        print("-" * 40)
    
    print()
    print("✅ Snappy wrapper working successfully!")
    print("🚀 You can now extend this to wrap compress/decompress functions!")

if __name__ == "__main__":
    main()