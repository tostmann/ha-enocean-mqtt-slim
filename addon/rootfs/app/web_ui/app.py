"""
Web UI Application
FastAPI-based web interface for device management
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="EnOcean MQTT Slim")

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "EnOcean MQTT Slim",
        "status": "Running"
    })


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/api/status")
async def get_status():
    """Get service status"""
    return {
        "status": "running",
        "eep_profiles": 1,
        "devices": 0,
        "gateway_connected": True
    }
