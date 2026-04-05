import json
import os
import secrets
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
STORE_FILE = DATA_DIR / "drops.json"
EXPIRY_SECONDS = 86400  # 24 hours


def load_drops() -> dict:
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return {}


def save_drops(drops: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(json.dumps(drops))


def cleanup_expired():
    drops = load_drops()
    now = time.time()
    expired = [k for k, v in drops.items() if now - v["created_at"] > EXPIRY_SECONDS]
    if expired:
        for k in expired:
            del drops[k]
        save_drops(drops)


class EncryptedPayload(BaseModel):
    encrypted_data: str


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request, "drop.html", {"mode": "landing"})


@app.post("/api/drops")
async def create_drop():
    cleanup_expired()
    drops = load_drops()
    drop_id = secrets.token_urlsafe(16)
    drops[drop_id] = {"encrypted_data": None, "created_at": time.time()}
    save_drops(drops)
    return {"id": drop_id}


@app.get("/drop/{drop_id}", response_class=HTMLResponse)
async def view_drop(request: Request, drop_id: str):
    return templates.TemplateResponse(request, "drop.html", {"mode": "drop", "drop_id": drop_id})


@app.get("/api/drops/{drop_id}")
async def get_drop(drop_id: str):
    cleanup_expired()
    drops = load_drops()
    if drop_id not in drops:
        raise HTTPException(status_code=404, detail="Not found or expired")
    drop = drops[drop_id]
    return {
        "has_data": drop["encrypted_data"] is not None,
        "encrypted_data": drop["encrypted_data"],
    }


@app.post("/api/drops/{drop_id}/data")
async def submit_data(drop_id: str, payload: EncryptedPayload):
    cleanup_expired()
    drops = load_drops()
    if drop_id not in drops:
        raise HTTPException(status_code=404, detail="Not found or expired")
    if drops[drop_id]["encrypted_data"] is not None:
        raise HTTPException(status_code=409, detail="Data already submitted")
    drops[drop_id]["encrypted_data"] = payload.encrypted_data
    save_drops(drops)
    return {"ok": True}


@app.delete("/api/drops/{drop_id}")
async def burn_drop(drop_id: str):
    cleanup_expired()
    drops = load_drops()
    if drop_id not in drops:
        raise HTTPException(status_code=404, detail="Not found or expired")
    del drops[drop_id]
    save_drops(drops)
    return {"burned": True}
