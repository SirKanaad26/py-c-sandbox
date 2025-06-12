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
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Can also be run using python directly.
python3 app.py
```

### 4. Access the Application
Open your browser and go to: **http://localhost:8000**

## API Endpoints

- `GET /` - Web interface
- `POST /compress/` - Compression endpoint
- `GET /health` - Health check
- `GET /debug/test-error` - Test error handling

## Steps to generate .so file
```
python3 setup.py build_ext --inplace
```

## Steps to activate emsdk

```
./emsdk activate latest
source ./emsdk_env.sh
emcc --version
```