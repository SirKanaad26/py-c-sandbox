#!/usr/bin/env python3
"""
Test the WASM built directly from Google's actual Snappy source files
"""

import os
from wasmtime import Store, Module, Instance


def test_snappy_direct_wasm():
    """Test the WASM built from actual Snappy source files"""
    wasm_path = "snappy_direct.wasm"
    
    if not os.path.exists(wasm_path):
        print(f"❌ WASM file not found: {wasm_path}")
        print("💡 Run ./build_from_snappy_source.sh first")
        return
    
    print("🗜️  Testing WASM Built from Actual Snappy Source Files")
    print("=" * 60)
    
    # Load WASM
    store = Store()
    
    with open(wasm_path, 'rb') as f:
        wasm_bytes = f.read()
    
    module = Module(store.engine, wasm_bytes)
    instance = Instance(store, module, [])
    exports = instance.exports(store)
    
    print("📦 Available functions:")
    for name in exports.keys():
        print(f"  - {name}")
    print()
    
    # Get functions
    max_compressed_func = exports["MaxCompressedLength"]
    version_func = exports["GetVersion"]
    
    print(f"📋 Version: {version_func(store)}")
    print()
    
    # Test with various sizes
    test_sizes = [0, 10, 100, 1000, 10000, 100000, 1000000, 10000000]
    
    print("📏 Results from Actual Google Snappy Source:")
    print(f"{'Input Size':>12} | {'Max Compressed':>14} | {'Overhead':>10} | {'Overhead %':>11}")
    print("-" * 60)
    
    for size in test_sizes:
        # Call the actual Snappy function compiled to WASM
        wasm_result = max_compressed_func(store, size)
        overhead = wasm_result - size
        overhead_pct = (overhead / size * 100) if size > 0 else 0
        
        print(f"{size:12,} | {wasm_result:14,} | {overhead:10,} | {overhead_pct:10.1f}%")
    
    # Performance test
    print(f"\n⚡ Performance Test (Actual Snappy Source)")
    print("-" * 45)
    
    import time
    iterations = 100000
    test_size = 1000
    
    start_time = time.time()
    for _ in range(iterations):
        max_compressed_func(store, test_size)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time_us = (total_time / iterations) * 1_000_000
    calls_per_sec = iterations / total_time
    
    print(f"Iterations: {iterations:,}")
    print(f"Total time: {total_time:.3f} seconds")
    print(f"Average per call: {avg_time_us:.3f} μs")
    print(f"Calls per second: {calls_per_sec:,.0f}")
    
    print(f"\n🎉 Test completed using unmodified Google Snappy source!")


if __name__ == "__main__":
    test_snappy_direct_wasm()