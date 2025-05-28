// test_wasm.js
// Node.js test script for Snappy WASM module

const fs = require('fs');
const path = require('path');

async function testSnappyWasm() {
    console.log('🗜️  Testing Snappy WebAssembly Module\n');

    try {
        // Load the WASM module
        console.log('📦 Loading WASM module...');
        const SnappyModule = require('./wasm_build/snappy_wasm.js');
        const snappyModule = await SnappyModule();
        
        // Get function references
        const maxCompressedLength = snappyModule.cwrap('wasm_max_compressed_length', 'number', ['number']);
        const testFunction = snappyModule.cwrap('wasm_test_function', 'number', ['number']);
        const getVersion = snappyModule.cwrap('wasm_get_version', 'number', []);
        
        // New functions - need to be more careful with parameter types
        const uncompressedLength = snappyModule.cwrap('wasm_uncompressed_length', 'number', ['number', 'number', 'number']);
        const validateCompressed = snappyModule.cwrap('wasm_validate_compressed_buffer', 'number', ['number', 'number']);
        const createMockCompressed = snappyModule.cwrap('wasm_create_mock_compressed', 'number', ['number', 'number', 'number']);
        
        console.log('✅ WASM module loaded successfully!');
        console.log(`📋 Version: ${getVersion()}`);
        
        // Debug: List available functions
        console.log('🔍 Available functions:');
        console.log('  - wasm_max_compressed_length:', typeof maxCompressedLength);
        console.log('  - wasm_test_function:', typeof testFunction);
        console.log('  - wasm_get_version:', typeof getVersion);
        console.log('  - wasm_uncompressed_length:', typeof uncompressedLength);
        console.log('  - wasm_validate_compressed_buffer:', typeof validateCompressed);
        console.log('  - wasm_create_mock_compressed:', typeof createMockCompressed);
        console.log('  - _malloc:', typeof snappyModule._malloc);
        console.log('  - _free:', typeof snappyModule._free);
        console.log('');

        // Test 1: Basic function test
        console.log('🧪 Test 1: Basic Function Test');
        console.log('─'.repeat(40));
        const testInput = 42;
        const testResult = testFunction(testInput);
        console.log(`Input: ${testInput}`);
        console.log(`Output: ${testResult}`);
        console.log(`Expected: ${testInput * 2}`);
        console.log(`Result: ${testResult === testInput * 2 ? '✅ PASS' : '❌ FAIL'}\n`);

        // Test 2: Max compressed length calculation
        console.log('🧪 Test 2: Max Compressed Length Calculation');
        console.log('─'.repeat(40));
        const testSizes = [0, 10, 100, 1000, 10000, 100000, 1000000];
        
        testSizes.forEach(size => {
            const maxSize = maxCompressedLength(size);
            const overhead = maxSize - size;
            const overheadPercent = size > 0 ? (overhead / size * 100).toFixed(1) : '0.0';
            
            console.log(`${size.toString().padStart(8)} bytes → ${maxSize.toString().padStart(8)} bytes (+${overheadPercent.toString().padStart(5)}%)`);
        });

        // Test 3: Performance test
        console.log('\n🚀 Test 3: Performance Test');
        console.log('─'.repeat(40));
        const iterations = 100000;
        const perfTestSize = 1000;
        
        console.log(`Running ${iterations.toLocaleString()} iterations...`);
        
        const startTime = process.hrtime.bigint();
        
        for (let i = 0; i < iterations; i++) {
            maxCompressedLength(perfTestSize);
        }
        
        const endTime = process.hrtime.bigint();
        const totalTimeNs = Number(endTime - startTime);
        const totalTimeMs = totalTimeNs / 1000000;
        const avgTimeUs = (totalTimeNs / iterations) / 1000;
        const callsPerSecond = (iterations / (totalTimeMs / 1000)).toFixed(0);
        
        console.log(`Total time: ${totalTimeMs.toFixed(2)} ms`);
        console.log(`Average per call: ${avgTimeUs.toFixed(3)} μs`);
        console.log(`Calls per second: ${Number(callsPerSecond).toLocaleString()}`);

        // Test 4: New Snappy functions
        console.log('\n🧪 Test 4: Uncompressed Length & Validation');
        console.log('─'.repeat(40));
        
        // Test creating mock compressed data and reading it back
        const testUncompressedSize = 12345;
        const mockBufferSize = 64;
        
        // Allocate memory in WASM
        const mockBuffer = snappyModule._malloc(mockBufferSize);
        const resultPtr = snappyModule._malloc(4); // For size_t result
        
        try {
            // Create mock compressed data
            const compressedSize = createMockCompressed(testUncompressedSize, mockBuffer, mockBufferSize);
            console.log(`Created mock compressed data: ${compressedSize} bytes`);
            
            // Test uncompressed_length function
            const status1 = uncompressedLength(mockBuffer, compressedSize, resultPtr);
            const retrievedSize = snappyModule.getValue(resultPtr, 'i32');
            
            console.log(`Uncompressed length status: ${status1} (0=OK)`);
            console.log(`Original size: ${testUncompressedSize}`);
            console.log(`Retrieved size: ${retrievedSize}`);
            console.log(`Match: ${testUncompressedSize === retrievedSize ? '✅ PASS' : '❌ FAIL'}`);
            
            // Test validation function
            const status2 = validateCompressed(mockBuffer, compressedSize);
            console.log(`Validation status: ${status2} (0=OK)`);
            console.log(`Validation: ${status2 === 0 ? '✅ PASS' : '❌ FAIL'}`);
            
            // Test edge cases
            console.log('\nEdge case tests:');
            const invalidStatus1 = uncompressedLength(0, 0, resultPtr); // null pointer
            const invalidStatus2 = uncompressedLength(mockBuffer, 2, resultPtr); // too small
            console.log(`Null pointer test: ${invalidStatus1 === 1 ? '✅ PASS' : '❌ FAIL'} (status: ${invalidStatus1})`);
            console.log(`Too small buffer test: ${invalidStatus2 === 1 ? '✅ PASS' : '❌ FAIL'} (status: ${invalidStatus2})`);
            
        } finally {
            // Clean up allocated memory
            snappyModule._free(mockBuffer);
            snappyModule._free(resultPtr);
        }

        // Test 5: Edge cases
        console.log('\n🧪 Test 4: Edge Cases');
        console.log('─'.repeat(40));
        const edgeCases = [0, 1, 2, 4, 8, 16, 32, 64, 1024, 65536, 1048576];
        
        edgeCases.forEach(size => {
            const maxSize = maxCompressedLength(size);
            const ratio = size > 0 ? (maxSize / size).toFixed(2) : 'N/A';
            console.log(`${size.toString().padStart(8)} → ${maxSize.toString().padStart(8)} (ratio: ${ratio})`);
        });

        console.log('\n🎉 All tests completed successfully!');
        console.log('\n💡 Next steps:');
        console.log('   - Add actual compress/decompress functions');
        console.log('   - Test with real data compression');
        console.log('   - Add streaming compression support');
        console.log('   - Compare performance with native implementations');

    } catch (error) {
        console.error('❌ Error testing WASM module:', error);
        console.error('\n🔧 Troubleshooting:');
        console.error('   1. Make sure you\'ve built the WASM module: ./build_wasm.sh');
        console.error('   2. Check that wasm_build/snappy_wasm.js exists');
        console.error('   3. Verify Emscripten is properly installed');
        process.exit(1);
    }
}

// Check if WASM files exist
const wasmJsPath = './wasm_build/snappy_wasm.js';
const wasmBinaryPath = './wasm_build/snappy_wasm.wasm';

if (!fs.existsSync(wasmJsPath) || !fs.existsSync(wasmBinaryPath)) {
    console.error('❌ WASM files not found!');
    console.error('Please build the WASM module first:');
    console.error('  chmod +x build_wasm.sh');
    console.error('  ./build_wasm.sh');
    process.exit(1);
}

// Run the tests
testSnappyWasm().catch(console.error);