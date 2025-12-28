#!/usr/bin/env python3
"""API FastAPI para o GrowBot"""

import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GrowBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_latest_output(provider: str) -> dict:
    """Pega o output mais recente de um provider."""
    output_dir = Path("output")
    files = sorted(output_dir.glob(f"*{provider}*.json"), reverse=True)
    if files:
        with open(files[0]) as f:
            return json.load(f)
    return {"items": []}

def get_input_text() -> str:
    """Pega o texto do input original."""
    exports_dir = Path("exports")
    for txt in exports_dir.glob("*.txt"):
        with open(txt, encoding="utf-8") as f:
            return f.read()
    return ""

@app.get("/api/data")
def get_data():
    return {
        "input": get_input_text(),
        "claude": get_latest_output("claude"),
        "openai": get_latest_output("openai"),
    }

@app.get("/api/items/{provider}")
def get_items(provider: str):
    return get_latest_output(provider)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
