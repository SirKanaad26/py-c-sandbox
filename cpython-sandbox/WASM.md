# WebAssembly C to WASM Compilation Guide

This guide covers compiling C code to WebAssembly and running it both in the browser and via command-line tools.

## 1. Install Required Tools

### Install LLVM (macOS)
```bash
brew install llvm
echo 'export PATH="/opt/homebrew/opt/llvm/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### You can also temporarily add it to your PATH for the current session:
```bash
export PATH="$(brew --prefix llvm)/bin:$PATH"
```

### Make sure WebAssembly tools are installed
```bash
brew install wabt binaryen
```

### Check if the tools are now available
```bash
llvm-dis --version
llc --version
wasm-ld --version
wasm2wat --version
```

### Install WASI-SDK
```bash
mkdir -p ~/wasi-sdk
cd ~/wasi-sdk
curl -LO https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-macos.tar.gz
tar xf wasi-sdk-20.0-macos.tar.gz
export WASI_SDK_PATH=~/wasi-sdk/wasi-sdk-20.0
export PATH=$WASI_SDK_PATH/bin:$PATH
```

### Install WebAssembly Runtime (Wasmtime)
```bash
brew install wasmtime
```


## 3. Compile C to WebAssembly

### Compile to Object File
```bash
$WASI_SDK_PATH/bin/clang --target=wasm32-wasi -c hello_new.c -o hello_new.o
```

### Link to WASM (With Function Exports)
```bash
$WASI_SDK_PATH/bin/wasm-ld --export=hello_world --export=calculate \
  --features=+bulk-memory \
  hello_new.o -o hello_new.wasm
```

## 4. Run WebAssembly from Command Line

```bash
wasmtime hello_new.wasm
```

### Serve the HTML File
```bash
python -m http.server
```

Visit `http://localhost:8000` in your browser.