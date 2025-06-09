from fastapi import FastAPI, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from wasm_runtime.wasm_executor import SnappyWasm

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

snappy = SnappyWasm("snappy_bindings/snappy.wasm")

@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/compress/")
async def compress_text(data: str = Form(...)):
    input_bytes = data.encode("utf-8")
    compressed = snappy.compress(input_bytes)
    return {"original_size": len(input_bytes), "compressed_size": len(compressed)}
