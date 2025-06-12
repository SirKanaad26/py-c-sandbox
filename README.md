# Sandboxing in Python
This repo contains the source code for all the experiments we did as part of CSE 227 project.

# Instructions to run code

A FastAPI web application for testing Snappy compression with both sandboxed and unsandboxed modes.

## Quick Start

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Project Structure
```
project/
├── app.py                 # FastAPI backend
└── static/
    ├── index.html        # Frontend HTML
    ├── styles.css        # Styling
    └── script.js         # JavaScript logic
```

### 3. Run the Application
```bash
# Development mode (with auto-reload)
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python app.py
```

### 4. Access the Application
Open your browser and go to: **http://localhost:8000**

## Features

- 🔄 **Two compression modes**: Sandboxed and Unsandboxed
- 📊 **Real-time statistics**: Compression ratio, space saved
- 📋 **Copy to clipboard**: Easy sharing of compressed data
- 🔍 **Error handling**: Detailed error messages for debugging
- 📁 **File upload support**: Drag & drop or click to select files

## API Endpoints

- `GET /` - Web interface
- `POST /compress/` - Compression endpoint
- `GET /health` - Health check
- `GET /debug/test-error` - Test error handling

## Troubleshooting

If you see "Invalid compressed length" errors, this indicates an issue with your sandboxed Snappy implementation. Try using the unsandboxed mode instead.


# Instructions to run code
python setup.py build_ext --inplace
python app/main.py



Steps to activate emsdk:
```
./emsdk activate latest
source ./emsdk_env.sh
emcc --version
```