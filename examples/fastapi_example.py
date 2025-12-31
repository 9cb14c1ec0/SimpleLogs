"""
FastAPI integration example for SimpleLogs
"""

from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
import httpx
from typing import Any
from datetime import datetime


class AsyncSimpleLogger:
    """Async version of SimpleLogger for use with FastAPI."""

    def __init__(self, base_url: str, api_key: str, source: str | None = None):
        self.url = f"{base_url}/api/v1/ingest"
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        self.source = source
        self.client: httpx.AsyncClient | None = None

    async def start(self):
        self.client = httpx.AsyncClient(timeout=5.0)

    async def stop(self):
        if self.client:
            await self.client.aclose()

    async def _send(self, level: str, message: str, metadata: dict[str, Any] | None = None):
        if not self.client:
            return

        payload = {
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if metadata:
            payload["metadata"] = metadata
        if self.source:
            payload["source"] = self.source

        try:
            await self.client.post(self.url, json=payload, headers=self.headers)
        except Exception:
            pass  # Fire and forget

    async def debug(self, message: str, metadata: dict[str, Any] | None = None):
        await self._send("debug", message, metadata)

    async def info(self, message: str, metadata: dict[str, Any] | None = None):
        await self._send("info", message, metadata)

    async def warn(self, message: str, metadata: dict[str, Any] | None = None):
        await self._send("warn", message, metadata)

    async def error(self, message: str, metadata: dict[str, Any] | None = None):
        await self._send("error", message, metadata)

    async def fatal(self, message: str, metadata: dict[str, Any] | None = None):
        await self._send("fatal", message, metadata)


# Initialize logger
logger = AsyncSimpleLogger(
    base_url="http://localhost",
    api_key="YOUR_API_KEY",
    source="fastapi-app",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await logger.start()
    yield
    await logger.stop()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request and response."""
    await logger.info(f"{request.method} {request.url.path}", {
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else None,
    })

    response = await call_next(request)

    if response.status_code >= 400:
        await logger.warn(f"Request failed with {response.status_code}", {
            "path": request.url.path,
            "status_code": response.status_code,
        })

    return response


@app.get("/")
async def index():
    return {"message": "Hello, World!"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    await logger.debug(f"Fetching user {user_id}", {"user_id": user_id})

    # Simulate user lookup
    user = {"id": user_id, "name": "John Doe"}

    await logger.info(f"User {user_id} retrieved", {"user_id": user_id})
    return user


@app.post("/orders")
async def create_order(order: dict):
    await logger.info("Order created", {
        "user_id": order.get("user_id"),
        "items": len(order.get("items", [])),
        "total": order.get("total"),
    })

    return {"order_id": 12345, "status": "created"}


@app.get("/error")
async def trigger_error():
    await logger.error("Intentional error triggered", {"endpoint": "/error"})
    raise HTTPException(status_code=500, detail="Something went wrong")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
