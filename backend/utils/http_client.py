"""
btctool 3.0 - High Performance Async HTTP Client
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("btctool.http")

# Default headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
        _client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            limits=limits,
            timeout=httpx.Timeout(6.0, connect=3.0),
            http2=False
        )
    return _client

async def close_http_client():
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None

async def fetch_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
    client = get_http_client()
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        resp = await client.get(url, params=params, headers=merged_headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"HTTP {resp.status_code} from {url}")
        return None
    except Exception as e:
        logger.error(f"HTTP request error fetching {url}: {e}")
        return None
