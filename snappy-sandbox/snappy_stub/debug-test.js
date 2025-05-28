// debug_test.js
// Simple test to see what functions are available

async function debugModule() {
    try {
        console.log('Loading WASM module...');
        const SnappyModule = require('./wasm_build/snappy_wasm.js');
        const snappyModule = await SnappyModule();
        
        console.log('Module loaded successfully!');
        
        // Try to get basic functions
        console.log('\n=== Testing Basic Functions ===');
        try {
            const getVersion = snappyModule.cwrap('wasm_get_version', 'number', []);
            console.log('✅ wasm_get_version:', getVersion());
        } catch (e) {
            console.log('❌ wasm_get_version failed:', e.message);
        }
        
        try {
            const testFunction = snappyModule.cwrap('wasm_test_function', 'number', ['number']);
            console.log('✅ wasm_test_function:', testFunction(21));
        } catch (e) {
            console.log('❌ wasm_test_function failed:', e.message);
        }
        
        try {
            const maxCompressedLength = snappyModule.cwrap('wasm_max_compressed_length', 'number', ['number']);
            console.log('✅ wasm_max_compressed_length:', maxCompressedLength(100));
        } catch (e) {
            console.log('❌ wasm_max_compressed_length failed:', e.message);
        }
        
        // Try new functions
        console.log('\n=== Testing New Functions ===');
        try {
            const uncompressedLength = snappyModule.cwrap('wasm_uncompressed_length', 'number', ['number', 'number', 'number']);
            console.log('✅ wasm_uncompressed_length: available');
        } catch (e) {
            console.log('❌ wasm_uncompressed_length failed:', e.message);
        }
        
        try {
            const validateCompressed = snappyModule.cwrap('wasm_validate_compressed_buffer', 'number', ['number', 'number']);
            console.log('✅ wasm_validate_compressed_buffer: available');
        } catch (e) {
            console.log('❌ wasm_validate_compressed_buffer failed:', e.message);
        }
        
        try {
            const createMockCompressed = snappyModule.cwrap('wasm_create_mock_compressed', 'number', ['number', 'number', 'number']);
            console.log('✅ wasm_create_mock_compressed: available');
        } catch (e) {
            console.log('❌ wasm_create_mock_compressed failed:', e.message);
        }
        
        // Check memory functions
        console.log('\n=== Testing Memory Functions ===');
        console.log('_malloc:', typeof snappyModule._malloc);
        console.log('_free:', typeof snappyModule._free);
        console.log('getValue:', typeof snappyModule.getValue);
        console.log('setValue:', typeof snappyModule.setValue);
        
    } catch (error) {
        console.error('Failed to load module:', error);
    }
}

debugModule();