"""
btctool 3.0 - High Performance FastAPI Application Server
"""

import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config import TIMEFRAMES, APP_NAME, VERSION
from backend.services.engine import get_summary_for_timeframe, warmup_cache_loop, _timeframe_cache
from backend.services.decision_matrix import calculate_cross_timeframe_alignment
from backend.utils.http_client import close_http_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("btctool.app")

_server_start_time = time.time()
_warmup_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch cache warmer
    global _warmup_task
    logger.info(f"Starting {APP_NAME} v{VERSION}...")
    _warmup_task = asyncio.create_task(warmup_cache_loop())
    yield
    # Shutdown
    logger.info("Shutting down btctool 3.0...")
    if _warmup_task:
        _warmup_task.cancel()
    await close_http_client()

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """
    Lightweight health check for UptimeRobot 24/7 cloud keep-alive.
    Accepts both GET and HEAD methods.
    """
    uptime_sec = int(time.time() - _server_start_time)
    return JSONResponse(
        content={
            "status": "healthy",
            "app": APP_NAME,
            "version": VERSION,
            "uptime_seconds": uptime_sec,
            "cached_timeframes": list(_timeframe_cache.keys()),
        },
        status_code=200
    )

@app.get("/btc/summary")
async def get_summary(timeframe: str = Query(default="1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 1w)")):
    """Returns real-time quantitative trading summary & directives for requested timeframe."""
    tf = timeframe.lower()
    if tf not in TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe '{timeframe}'. Supported: {TIMEFRAMES}")
    
    data = await get_summary_for_timeframe(tf)
    if "error" in data:
        raise HTTPException(status_code=502, detail=data["error"])
    return data

@app.get("/btc/cross-alignment")
async def get_cross_alignment():
    """Returns 9-timeframe consensus alignment score."""
    alignment = calculate_cross_timeframe_alignment(_timeframe_cache)
    return alignment

# Frontend Static Files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def root():
    """Serves trading terminal dashboard."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"{APP_NAME} Backend Operational. Frontend at /static."}
