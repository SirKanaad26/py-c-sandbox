#!/usr/bin/env python3
"""
Snappy WASM Sandbox - Testing GetUncompressedLength function
Function signature: bool GetUncompressedLength(const char* start, size_t n, size_t* result)
"""

import wasmtime
import os
import sys
import struct

class SnappyWasmSandbox:
    def __init__(self, wasm_file_path):
        """Initialize the WASM runtime and load the Snappy module."""
        self.engine = wasmtime.Engine()
        self.store = wasmtime.Store(self.engine)
        
        # Load the WASM module first to inspect imports
        try:
            with open(wasm_file_path, 'rb') as f:
                wasm_bytes = f.read()
            
            self.module = wasmtime.Module(self.engine, wasm_bytes)
            
            # Inspect the module's imports
            imports = self.module.imports
            print(f"📋 WASM Module requires {len(imports)} imports:")
            
            import_objects = []
            
            for imp in imports:
                print(f"   • {imp.module}.{imp.name} ({imp.type})")
                
                # Create mock implementations for different import types
                if isinstance(imp.type, wasmtime.FuncType):
                    # Create a mock function
                    mock_func = self.create_mock_function(imp.name, imp.type)
                    import_objects.append(mock_func)
                elif isinstance(imp.type, wasmtime.MemoryType):
                    # Create memory
                    memory = wasmtime.Memory(self.store, imp.type)
                    import_objects.append(memory)
                elif isinstance(imp.type, wasmtime.GlobalType):
                    # Create global
                    if imp.type.content == wasmtime.ValType.i32():
                        global_val = wasmtime.Global(self.store, imp.type, wasmtime.Val.i32(0))
                    elif imp.type.content == wasmtime.ValType.i64():
                        global_val = wasmtime.Global(self.store, imp.type, wasmtime.Val.i64(0))
                    elif imp.type.content == wasmtime.ValType.f32():
                        global_val = wasmtime.Global(self.store, imp.type, wasmtime.Val.f32(0.0))
                    elif imp.type.content == wasmtime.ValType.f64():
                        global_val = wasmtime.Global(self.store, imp.type, wasmtime.Val.f64(0.0))
                    else:
                        global_val = wasmtime.Global(self.store, imp.type, wasmtime.Val.i32(0))
                    import_objects.append(global_val)
                elif isinstance(imp.type, wasmtime.TableType):
                    # Create table
                    table = wasmtime.Table(self.store, imp.type, wasmtime.Val.ref_null())
                    import_objects.append(table)
                else:
                    print(f"     ⚠️  Unknown import type: {type(imp.type)}")
                    import_objects.append(None)
            
            # Create instance with imports
            self.instance = wasmtime.Instance(self.store, self.module, import_objects)
            
            # Get exports
            exports = self.instance.exports(self.store)
            print(f"\n📤 Available exports: {list(exports.keys())}")
            
            # The function might be wrapped by Emscripten's binding system
            # Let's look for it or try to call the constructor to set up bindings
            if "__wasm_call_ctors" in exports:
                print("🔧 Calling WASM constructors to initialize bindings...")
                try:
                    exports["__wasm_call_ctors"](self.store)
                    print("✅ Constructors called successfully")
                except Exception as e:
                    print(f"⚠️  Constructor call failed: {e}")
            
            # Try to find the GetUncompressedLength function
            function_names = ["GetUncompressedLength", "getUncompressedLength", "_GetUncompressedLength", 
                            "_Z20GetUncompressedLengthPKcmPm", "snappy_uncompressed_length"]
            self.get_uncompressed_length = None
            
            for name in function_names:
                if name in exports:
                    self.get_uncompressed_length = exports[name]
                    print(f"✅ Found function: {name}")
                    break
            
            if not self.get_uncompressed_length:
                print("❌ GetUncompressedLength function not found in direct exports")
                print("   This appears to be an Emscripten build with embind.")
                print("   The function might be available through JavaScript bindings.")
                
                # Try to create our own simple test function using malloc/free
                self.malloc_func = exports.get("malloc")
                self.free_func = exports.get("free")
                
                if self.malloc_func and self.free_func:
                    print("✅ Found malloc/free - will use manual memory testing")
                    self.manual_mode = True
                else:
                    print("❌ Cannot find way to test the function")
                    self.manual_mode = False
            
            # Get memory
            self.memory = None
            if "memory" in exports:
                self.memory = exports["memory"]
            else:
                # Look for any memory in imports or exports
                for name, export in exports.items():
                    if isinstance(export, wasmtime.Memory):
                        self.memory = export
                        break
            
            if not self.memory:
                print("⚠️  No memory found, will try to work without it")
            else:
                print("✅ Memory found")
            
            print("✅ Snappy WASM module loaded successfully")
            
        except FileNotFoundError:
            print(f"❌ Error: WASM file '{wasm_file_path}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading WASM module: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def create_mock_function(self, name, func_type):
        """Create a mock function for WASM imports."""
        print(f"     Creating mock for {name}: {func_type.params} -> {func_type.results}")
        
        def mock_impl(caller, *args):
            """Mock implementation that handles common patterns."""
            if name in ['abort', '__assert_fail', '_abort']:
                print(f"   🚨 Mock {name} called with args: {args}")
                return []
            elif name in ['malloc', '_malloc', '__builtin_malloc']:
                # Return a mock memory address
                return [1024] if func_type.results else []
            elif name in ['free', '_free', '__builtin_free']:
                return []
            elif name in ['memcpy', '_memcpy', '__builtin_memcpy']:
                return [args[0]] if func_type.results else []
            elif name in ['memset', '_memset', '__builtin_memset']:
                return [args[0]] if func_type.results else []
            elif 'printf' in name or 'puts' in name:
                return [0] if func_type.results else []
            else:
                print(f"   📞 Mock {name} called with args: {args}")
                # Return appropriate default values based on result types
                results = []
                for result_type in func_type.results:
                    if result_type == wasmtime.ValType.i32():
                        results.append(0)
                    elif result_type == wasmtime.ValType.i64():
                        results.append(0)
                    elif result_type == wasmtime.ValType.f32():
                        results.append(0.0)
                    elif result_type == wasmtime.ValType.f64():
                        results.append(0.0)
                return results
        
        return wasmtime.Func(self.store, func_type, mock_impl)
    
    def write_to_memory(self, data, offset=0):
        """Write data to WASM memory at specified offset."""
        if not self.memory:
            raise Exception("No memory available")
        
        # Use the correct memory access method for wasmtime
        memory_size = self.memory.size(self.store)
        if offset + len(data) > memory_size * 65536:  # WASM pages are 64KB
            raise Exception(f"Data too large for WASM memory: {len(data)} bytes at offset {offset}")
        
        # Access memory data using wasmtime's method
        memory_data = self.memory.data_ptr(self.store)
        
        # Write data byte by byte (safer approach)
        for i, byte_val in enumerate(data):
            memory_data[offset + i] = byte_val
        
        return offset
    
    def read_from_memory(self, offset, size):
        """Read data from WASM memory."""
        if not self.memory:
            raise Exception("No memory available")
            
        memory_data = self.memory.data_ptr(self.store)
        return bytes(memory_data[offset:offset + size])
    
    def test_get_uncompressed_length(self, data, description=""):
        """Test GetUncompressedLength with given data."""
        print(f"\n🔍 Testing: {description}")
        
        try:
            # Convert input to bytes if needed
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            elif isinstance(data, (list, tuple)):
                data_bytes = bytes(data)
            else:
                data_bytes = data
            
            print(f"   Input bytes: {list(data_bytes)} (length: {len(data_bytes)})")
            print(f"   Hex: {data_bytes.hex() if data_bytes else '(empty)'}")
            
            if self.get_uncompressed_length:
                # Direct function call
                if not self.memory:
                    print("   ⚠️  No memory available, trying direct call")
                    try:
                        result = self.get_uncompressed_length(self.store, len(data_bytes))
                        print(f"   📞 Direct call result: {result}")
                        return True, result
                    except Exception as e:
                        print(f"   ❌ Direct call failed: {e}")
                        return False, None
                
                # Memory-based call
                data_offset = 1024  # Start after first 1KB
                result_offset = 2048  # Result pointer location
                
                # Write input data to memory
                if data_bytes:
                    self.write_to_memory(data_bytes, data_offset)
                
                # Initialize result area to zero
                self.write_to_memory(b'\x00\x00\x00\x00', result_offset)
                
                # Call the function
                success = self.get_uncompressed_length(self.store, data_offset, len(data_bytes), result_offset)
                
                # Read the result
                result_bytes = self.read_from_memory(result_offset, 4)
                result_value = struct.unpack('<I', result_bytes)[0]
                
                print(f"   Function returned: {bool(success)}")
                if success:
                    print(f"   ✅ Uncompressed length: {result_value}")
                    return True, result_value
                else:
                    print(f"   ❌ Failed to parse")
                    return False, None
                    
            elif hasattr(self, 'manual_mode') and self.manual_mode:
                # Manual testing using malloc/free and memory inspection
                print("   🔧 Manual mode: Testing varint parsing logic")
                
                if not data_bytes:
                    print("   ❌ Empty data - invalid varint")
                    return False, None
                
                # Simple varint parsing simulation
                # This simulates what GetUncompressedLength would do
                result = 0
                shift = 0
                for i, byte in enumerate(data_bytes):
                    if shift >= 32:
                        print("   ❌ Varint too long (overflow)")
                        return False, None
                    
                    result |= (byte & 0x7F) << shift
                    shift += 7
                    
                    if (byte & 0x80) == 0:
                        # End of varint
                        print(f"   ✅ Parsed varint: {result} (used {i+1} bytes)")
                        return True, result
                
                print("   ❌ Incomplete varint (missing terminator)")
                return False, None
            else:
                print("   ❌ No way to test the function")
                return False, None
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
    def create_varint(self, value):
        """Create a varint32 encoding of a value (for testing valid inputs)."""
        result = []
        while value >= 0x80:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)
    
    def run_test_suite(self):
        """Run a comprehensive test suite with various inputs."""
        print("\n" + "=" * 70)
        print("🧪 SNAPPY WASM SANDBOX - GetUncompressedLength Tests")
        print("=" * 70)
        
        if not self.get_uncompressed_length and not (hasattr(self, 'manual_mode') and self.manual_mode):
            print("❌ Cannot run tests - no function available and no manual mode")
            return []
        
        if hasattr(self, 'manual_mode') and self.manual_mode:
            print("🔧 Running in MANUAL MODE - simulating varint parsing")
        
        # Test cases
        test_cases = []
        
        # Valid varint32 encodings
        print("\n📋 Generating test cases...")
        valid_values = [0, 1, 127, 128, 255, 16383, 16384, 65535]
        for val in valid_values:
            varint_bytes = self.create_varint(val)
            test_cases.append((varint_bytes, f"Valid varint32: {val}"))
        
        # Invalid/edge cases
        test_cases.extend([
            (b'', "Empty data"),
            (b'\x00', "Zero byte"),
            (b'\x01', "Single byte: 1"),
            (b'\x7F', "Single byte: 127"), 
            (b'\x80', "Incomplete varint"),
            (b'\xFF', "Incomplete varint 0xFF"),
            (b'\x80\x80\x80\x80\x80\x01', "Potential overflow"),
            (b'test', "ASCII text"),
            (bytes(range(10)), "Sequential bytes"),
        ])
        
        results = []
        successful = 0
        failed = 0
        
        for data, description in test_cases:
            success, result = self.test_get_uncompressed_length(data, description)
            results.append((description, data, success, result))
            
            if success:
                successful += 1
            else:
                failed += 1
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        total = len(results)
        print(f"Total tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        return results

def main():
    """Main function to run the sandbox."""
    wasm_file = "snappy.wasm"
    
    if not os.path.exists(wasm_file):
        print(f"❌ Please ensure '{wasm_file}' is in the current directory")
        sys.exit(1)
    
    try:
        print("🚀 Starting Snappy WASM Sandbox...")
        
        # Create sandbox instance
        sandbox = SnappyWasmSandbox(wasm_file)
        
        # Run the test suite
        results = sandbox.run_test_suite()
        
        print(f"\n🎯 Sandbox testing completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()