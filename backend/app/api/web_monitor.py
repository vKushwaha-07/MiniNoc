from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import httpx
import time
import asyncio
from typing import List, Optional

router = APIRouter()

class WebTarget(BaseModel):
    url: HttpUrl
    name: str

class WebCheckResult(BaseModel):
    url: str
    status_code: int
    latency_ms: float
    is_up: bool
    error: Optional[str] = None

# In-memory storage for demo purposes (would be DB in prod)
targets = [
    {"url": "https://www.google.com", "name": "Google"},
    {"url": "https://www.cloudflare.com", "name": "Cloudflare"},
    {"url": "https://github.com", "name": "GitHub"},
]

@router.get("/targets", response_model=List[dict])
def get_targets():
    """Get list of monitored websites."""
    return targets

@router.post("/check", response_model=WebCheckResult)
async def check_website(target: WebTarget):
    """
    Check a single website's status and latency.
    Works in Vercel environment.
    """
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(str(target.url))
            latency = (time.time() - start_time) * 1000
            
            return WebCheckResult(
                url=str(target.url),
                status_code=response.status_code,
                latency_ms=round(latency, 2),
                is_up=response.status_code < 400
            )
    except Exception as e:
        return WebCheckResult(
            url=str(target.url),
            status_code=0,
            latency_ms=0,
            is_up=False,
            error=str(e)
        )

@router.post("/check-all", response_model=List[WebCheckResult])
async def check_all_websites():
    """Check all configured targets in parallel."""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        results = []
        for t in targets:
            start_time = time.time()
            try:
                response = await client.get(t["url"])
                latency = (time.time() - start_time) * 1000
                results.append(WebCheckResult(
                    url=t["url"],
                    status_code=response.status_code,
                    latency_ms=round(latency, 2),
                    is_up=response.status_code < 400
                ))
            except Exception as e:
                results.append(WebCheckResult(
                    url=t["url"],
                    status_code=0,
                    latency_ms=0,
                    is_up=False,
                    error=str(e)
                ))
        return results
