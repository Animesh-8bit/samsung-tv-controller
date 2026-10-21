"""
FastAPI Server for Samsung Smart TV Mac Controller
Serves the REST API and the Frontend Remote Interface
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.controller import controller
from core.discovery import discover_samsung_tvs
from core.keys import POPULAR_APPS

app = FastAPI(
    title="Samsung Smart TV Mac Controller",
    description="High-performance Mac controller for Samsung Tizen Smart TVs",
    version="1.0.0"
)

# Enable CORS for local app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"


# Pydantic Request Models
class KeyRequest(BaseModel):
    key: str

class KeysSequenceRequest(BaseModel):
    keys: List[str]
    delay: float = 0.25

class PowerRequest(BaseModel):
    action: str = "toggle"  # "toggle", "on", "off"

class AppRequest(BaseModel):
    app_id: str

class BrowserRequest(BaseModel):
    url: str

class TextRequest(BaseModel):
    text: str

class SeekRequest(BaseModel):
    seconds: int
    target_time: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    ip: Optional[str] = None
    mac: Optional[str] = None
    port: Optional[int] = None


@app.get("/api/status")
def get_status():
    """Returns TV connection state, power status, and metadata."""
    return controller.get_info()


@app.get("/api/apps")
def get_apps():
    """Returns list of popular installed Smart TV apps."""
    return {"apps": POPULAR_APPS}


@app.post("/api/key")
def send_key(req: KeyRequest):
    """Sends a single remote control key."""
    success, msg = controller.send_key(req.key)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "key": req.key}


@app.post("/api/keys")
def send_keys_sequence(req: KeysSequenceRequest):
    """Sends a sequence of keys with delay."""
    success, msg = controller.send_keys_sequence(req.keys, req.delay)
    return {"success": success, "message": msg}


@app.get("/api/media/status")
def get_media_status():
    """Returns current UPnP playback position and state if active."""
    return controller.get_upnp_playback_info()


@app.post("/api/seek")
def seek_media(req: SeekRequest):
    """
    Universal media seek across all streaming apps and local media.
    - If target_time is provided (e.g. '00:15:30') and UPnP is active, seeks to exact time.
    - Otherwise seeks relative seconds (e.g. -30, -10, +10, +30).
    """
    if req.target_time:
        success, msg = controller.seek_upnp(req.target_time)
    else:
        success, msg = controller.seek(req.seconds)

    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "seconds": req.seconds}



@app.post("/api/power")
def control_power(req: PowerRequest):
    """Powers TV on via Wake-on-LAN, powers off, or toggles."""
    action = req.action.lower()
    if action == "on":
        success, msg = controller.power_on()
    elif action == "off":
        success, msg = controller.power_off()
    else:
        success, msg = controller.power_toggle()

    return {"success": success, "message": msg, "action": action}


@app.post("/api/app")
def launch_app(req: AppRequest):
    """Launches an application by ID."""
    success, msg = controller.launch_app(req.app_id)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "app_id": req.app_id}


@app.post("/api/browser")
def open_browser(req: BrowserRequest):
    """Opens a URL in the TV's web browser."""
    success, msg = controller.open_browser(req.url)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "url": req.url}


@app.post("/api/text")
def send_text(req: TextRequest):
    """Sends text typing into TV."""
    success, msg = controller.send_text(req.text)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg}


@app.post("/api/discover")
def discover_tvs():
    """Scans local network via UPnP/SSDP to discover Samsung TVs."""
    tvs = discover_samsung_tvs(timeout=3.0)
    return {"discovered": tvs}


@app.get("/api/config")
def get_config():
    """Returns current controller network configuration."""
    return controller.config


@app.post("/api/config")
def update_config(req: ConfigUpdateRequest):
    """Updates TV IP, MAC, or Port."""
    controller.update_settings(ip=req.ip, mac=req.mac, port=req.port)
    return {"success": True, "config": controller.config}


# Serve Frontend Static Assets
if FRONTEND_DIR.exists():
    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/style.css")
    def serve_css():
        return FileResponse(str(FRONTEND_DIR / "style.css"), media_type="text/css")

    @app.get("/app.js")
    def serve_js():
        return FileResponse(str(FRONTEND_DIR / "app.js"), media_type="application/javascript")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=5588, reload=False)
