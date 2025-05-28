def py_capitalize(str input_str):
    import wasm_bridge
    return wasm_bridge.wasm_capitalize(input_str)
