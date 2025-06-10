# Makefile for Snappy Cython wrapper and WASM module

.PHONY: all build clean test install-deps wasm wasm-test wasm-clean help

# Default target
all: build

# Build the Cython extension
build:
	python setup.py build_ext --inplace

# Build WebAssembly module
wasm:
	chmod +x build_wasm.sh
	./build_wasm.sh

# Build simple WebAssembly module (mock implementation)
wasm-simple:
	chmod +x build_wasm_simple.sh
	./build_wasm_simple.sh

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf *.egg-info/
	rm -f snappy_wrapper.c
	rm -f snappy_wrapper*.so
	rm -f snappy_wrapper*.pyd
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Clean WASM build artifacts
wasm-clean:
	rm -rf wasm_build/

# Full clean
clean-all: clean wasm-clean

# Run the Cython test
test: build
	python main.py

# Run WASM tests (assumes WASM is already built)
wasm-test:
	@echo "🧪 Running Node.js WASM tests..."
	@if [ ! -f "wasm_build/snappy_wasm.js" ]; then \
		echo "❌ WASM files not found. Build first with 'make wasm' or 'make wasm-simple'"; \
		exit 1; \
	fi
	node test_wasm.js
	@echo ""
	@echo "🌐 To test in browser, open test_wasm.html in a web server"
	@echo "   Quick server: python -m http.server 8000"

# Run WASM tests (build simple version first)
wasm-test-simple: wasm-simple
	@echo "🧪 Running Node.js WASM tests (simple version)..."
	node test_wasm.js
	@echo ""
	@echo "🌐 To test in browser, open test_wasm.html in a web server"
	@echo "   Quick server: python -m http.server 8000"

# Install system dependencies (Ubuntu/Debian)
install-deps-ubuntu:
	sudo apt-get update
	sudo apt-get install -y libsnappy-dev python3-dev nodejs
	pip install cython setuptools

# Install system dependencies (macOS with Homebrew)
install-deps-macos:
	brew install snappy nodejs
	pip install cython setuptools

# Install system dependencies (CentOS/RHEL/Fedora)
install-deps-fedora:
	sudo dnf install -y snappy-devel python3-devel nodejs npm
	pip install cython setuptools

# Install Emscripten for WASM compilation
install-emscripten:
	@echo "Installing Emscripten..."
	git clone https://github.com/emscripten-core/emsdk.git
	cd emsdk && ./emsdk install latest && ./emsdk activate latest
	@echo "Run: source ./emsdk/emsdk_env.sh"

# Help
help:
	@echo "Available targets:"
	@echo "  build              - Build the Cython extension"
	@echo "  wasm               - Build WebAssembly module (full Snappy)"
	@echo "  wasm-simple        - Build WebAssembly module (mock implementation)"
	@echo "  clean              - Clean Cython build artifacts"
	@echo "  wasm-clean         - Clean WASM build artifacts"
	@echo "  clean-all          - Clean all build artifacts"
	@echo "  test               - Build and run Cython test"
	@echo "  wasm-test          - Run WASM tests (build first)"
	@echo "  wasm-test-simple   - Build simple WASM and run tests"
	@echo "  install-deps-ubuntu - Install dependencies on Ubuntu/Debian"
	@echo "  install-deps-macos  - Install dependencies on macOS"
	@echo "  install-deps-fedora - Install dependencies on Fedora/RHEL"
	@echo "  install-emscripten  - Install Emscripten for WASM compilation"
	@echo "  help               - Show this help"