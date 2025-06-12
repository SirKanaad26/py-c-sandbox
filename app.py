from fastapi import FastAPI, UploadFile, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from snappy_unsandboxed import snappy_wrapper
from snappy_sandbox.snappy.snappywasm import snappy_sandbox
import base64
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/compress/")
async def compress_text(data: str = Form(...), mode: str = Form(...)):
    input_bytes = data.encode("utf-8")
    logger.info(f"Compressing {len(input_bytes)} bytes in {mode} mode")
    
    try: 
        if mode == "sandboxed":
            logger.info("Using sandboxed compression")
            snappy_sandboxed = snappy_sandbox.SnappyWasm()
            compressed = snappy_sandboxed.compress(input_bytes)
            print("compressed type:", type(compressed))
            print("compressed length:", len(compressed) if compressed else "None")
            
            # Check if compression actually worked
            if compressed is None:
                raise Exception("Sandboxed compression returned None")
            
            if len(compressed) == 0:
                raise Exception("Sandboxed compression returned empty result")
            
        else:
            logger.info("Using unsandboxed compression")
            compressed = snappy_wrapper.compress_data(input_bytes)
            print("unsandboxed compressed length:", len(compressed) if compressed else "None")
            
            # Check if compression actually worked
            if compressed is None:
                raise Exception("Unsandboxed compression returned None")
                
            if len(compressed) == 0:
                raise Exception("Unsandboxed compression returned empty result")
        
        # If we get here, compression was successful
        encoded = base64.b64encode(compressed).decode("utf-8")
        
        result = {
            "error": False,
            "original_size": len(input_bytes),
            "compressed_size": len(compressed),
            "compressed_base64": encoded,
            "mode": mode
        }
        
        logger.info(f"Compression successful: {len(input_bytes)} -> {len(compressed)} bytes")
        return JSONResponse(content=result)
        
    except Exception as e:
        # Log the full error for debugging
        error_msg = str(e)
        logger.error(f"Compression failed: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        print(f"Crashed\n\n\n{e}\n\n\n\n\n\n")
        
        # Return proper error response instead of putting error in original_size
        error_response = {
            "error": True,
            "message": f"Compression failed: {error_msg}",
            "type": type(e).__name__,
            "mode": mode,
            "input_size": len(input_bytes)
        }
        
        # Return error with appropriate HTTP status
        return JSONResponse(status_code=500, content=error_response)