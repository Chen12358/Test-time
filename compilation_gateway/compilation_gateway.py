# compilation_gateway.py

import asyncio
import os
import httpx
import threading
import uvicorn
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict

# --- Configuration ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

WORKER_TIMEOUT = int(os.getenv("WORKER_TIMEOUT", "600"))

app = FastAPI(
    title="Distributed Lean Compilation Gateway",
    description="Routes single and batch compilation requests to a pool of workers.",
    version="2.1.0",
)

# --- Global State & Worker Management (Unchanged) ---
WORKER_POOL: List[str] = []
WORKER_INDEX = 0
worker_lock = threading.Lock()
GATEWAY_CLIENT: httpx.AsyncClient = None

@app.post("/register", status_code=200)
async def register_worker(request: Request):
    data = await request.json()
    worker_url = data.get("url")
    if not worker_url:
        raise HTTPException(status_code=400, detail="Request must include the worker 'url'.")
    with worker_lock:
        if worker_url not in WORKER_POOL:
            WORKER_POOL.append(worker_url)
            logger.info(f"Successfully registered new worker: {worker_url}")
        else:
            logger.info(f"Worker already registered: {worker_url}")
    return {"message": "Worker registered successfully"}

@app.get("/workers")
async def get_workers():
    with worker_lock:
        return {"active_workers": WORKER_POOL}

async def health_check_workers():
    while True:
        await asyncio.sleep(30)
        unhealthy_workers = []
        with worker_lock:
            workers_to_check = list(WORKER_POOL)
        for url in workers_to_check:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{url}/health")
                    if response.status_code != 200:
                        unhealthy_workers.append(url)
            except httpx.RequestError:
                unhealthy_workers.append(url)
        if unhealthy_workers:
            with worker_lock:
                for url in unhealthy_workers:
                    if url in WORKER_POOL:
                        WORKER_POOL.remove(url)
                        logger.warning(f"Removed unhealthy worker: {url}")

def get_next_worker() -> str:
    global WORKER_INDEX
    with worker_lock:
        if not WORKER_POOL:
            raise HTTPException(status_code=503, detail="Service Unavailable: No registered workers.")
        if WORKER_INDEX >= len(WORKER_POOL):
            WORKER_INDEX = 0
        worker_url = WORKER_POOL[WORKER_INDEX]
        WORKER_INDEX = (WORKER_INDEX + 1) % len(WORKER_POOL)
        return worker_url

# --- Request Forwarding (Unchanged) ---

async def forward_request(request: Request, target_endpoint: str):
    try:
        worker_url = get_next_worker()
    except HTTPException as e:
        raise e

    target_url = f"{worker_url}/{target_endpoint}"
    logger.info(f"Forwarding request to worker: {target_url}")
    
    body_bytes = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host']}

    try:
        worker_req = GATEWAY_CLIENT.build_request("POST", url=target_url, headers=headers, content=body_bytes)
        worker_resp = await GATEWAY_CLIENT.send(worker_req, stream=True)
        return StreamingResponse(
            worker_resp.aiter_bytes(),
            status_code=worker_resp.status_code,
            headers=worker_resp.headers,
        )
    except httpx.ConnectError:
        logger.error(f"Connection to worker {worker_url} failed.")
        raise HTTPException(status_code=502, detail="Bad Gateway: Could not connect to worker.")
    except httpx.ReadTimeout:
        logger.error(f"Read timeout while waiting for worker {worker_url}. It may be overloaded or the job is too long.")
        raise HTTPException(status_code=504, detail="Gateway Timeout: The worker took too long to respond.")


@app.post("/api/v1/compile")
async def forward_batch_request(request: Request):
    return await forward_request(request, "compile")

@app.post("/api/v1/compile_one")
async def forward_single_request(request: Request):
    return await forward_request(request, "compile_one")

@app.on_event("startup")
async def on_startup():
    global GATEWAY_CLIENT
    # ** KEY CHANGE: Use the configurable timeout when creating the client **
    logger.info(f"Gateway starting up. Timeout for worker requests set to {WORKER_TIMEOUT} seconds.")
    limits = httpx.Limits(max_connections=800, max_keepalive_connections=50)
    GATEWAY_CLIENT = httpx.AsyncClient(timeout=WORKER_TIMEOUT,limits=limits)
    asyncio.create_task(health_check_workers())

@app.on_event("shutdown")
async def on_shutdown():
    await GATEWAY_CLIENT.aclose()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9876)
    # uvicorn.run(app, host="0.0.0.0", port=9875)