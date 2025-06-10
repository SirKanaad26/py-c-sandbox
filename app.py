from fastapi import FastAPI, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from snappy_unsandboxed import snappy_wrapper
from snappy_sandbox.snappy.snappywasm import snappy_sandbox
import base64

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/compress/")
async def compress_text(data: str = Form(...), mode: str = Form(...)):
    input_bytes = data.encode("utf-8")
    try: 
        if mode == "sandboxed":
            snappy_sandboxed = snappy_sandbox.SnappyWasm()
            compressed = snappy_sandboxed.compress(input_bytes)
        else:
            compressed = snappy_wrapper.compress_data(input_bytes)
    except Exception as e:
        print(f"Crashed===================================\
              ====================\n==============================\
              ========================\n============================================\
              ==========\n======================================================{e}")

    encoded = base64.b64encode(compressed).decode("utf-8")
    return JSONResponse({
        "original_size": len(input_bytes),
        "compressed_size": len(compressed),
        "compressed_base64": encoded
    })

