# gateway.py
# This is the central API gateway server.
# It now routes requests and translates the model name for the worker.

import asyncio
import httpx
import threading
import uvicorn
import logging
import json
import argparse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any

# --- Basic Configuration ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unified vLLM Gateway",
    description="A gateway that routes and translates model names for vLLM workers.",
    version="2.3.0", # Version updated for bugfix
)

# --- Global State ---
WORKER_POOL: Dict[str, List[Dict[str, str]]] = {}
MODEL_INDICES: Dict[str, int] = {}
worker_lock = threading.Lock()

GATEWAY_CLIENT: httpx.AsyncClient = None

# --- Worker Management Endpoints & Logic ---

@app.post("/register", status_code=200)
async def register_worker(request: Request):
    """
    Workers must now provide their URL, friendly model name, and absolute model path.
    e.g., {"url": "...", "model_name": "Qwen3-32B", "model_path": "/scratch/..."}
    """
    try:
        data = await request.json()
        worker_url = data.get("url")
        model_name = data.get("model_name")
        model_path = data.get("model_path")
        if not all([worker_url, model_name, model_path]):
            raise HTTPException(status_code=400, detail="'url', 'model_name', and 'model_path' are required.")

        with worker_lock:
            if model_name not in WORKER_POOL:
                WORKER_POOL[model_name] = []
                MODEL_INDICES[model_name] = 0
                logger.info(f"First worker for model '{model_name}' registered. Creating new pool.")
            
            if not any(w['url'] == worker_url for w in WORKER_POOL[model_name]):
                worker_info = {"url": worker_url, "path": model_path}
                WORKER_POOL[model_name].append(worker_info)
                logger.info(f"Successfully registered new worker {worker_url} for model '{model_name}'")
            else:
                logger.info(f"Worker {worker_url} for model '{model_name}' already registered.")
        
        return {"message": "Worker registered successfully"}
    except Exception as e:
        logger.error(f"Error during worker registration: {e}")
        raise HTTPException(status_code=500, detail="Failed to register worker.")

@app.get("/workers")
async def get_workers():
    with worker_lock:
        return {"worker_pool": WORKER_POOL}

async def health_check_workers():
    while True:
        await asyncio.sleep(60)
        unhealthy_urls = set()
        
        with worker_lock:
            all_workers = {w['url'] for workers in WORKER_POOL.values() for w in workers}

        for url in all_workers:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{url}/health")
                    if response.status_code != 200:
                        unhealthy_urls.add(url)
            except httpx.RequestError:
                unhealthy_urls.add(url)

        if unhealthy_urls:
            with worker_lock:
                for url in unhealthy_urls:
                    for model_name, workers in list(WORKER_POOL.items()):
                        # Filter out the unhealthy worker
                        original_len = len(workers)
                        WORKER_POOL[model_name] = [w for w in workers if w['url'] != url]
                        if len(WORKER_POOL[model_name]) < original_len:
                            logger.info(f"Removed unhealthy worker {url} from model pool '{model_name}'")
                        # If a model pool becomes empty, remove it
                        if not WORKER_POOL[model_name]:
                            del WORKER_POOL[model_name]
                            del MODEL_INDICES[model_name]
                            logger.info(f"Model pool for '{model_name}' is now empty and has been removed.")


# --- Request Forwarding Logic ---

def get_next_worker_for_model(model_name: str) -> Dict[str, str]:
    """
    Selects the next worker for a model and returns its info (url and path).
    This function is now robust against workers being removed.
    """
    global MODEL_INDICES
    with worker_lock:
        if model_name not in WORKER_POOL or not WORKER_POOL[model_name]:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found or no available workers.")
        
        workers = WORKER_POOL[model_name]
        current_index = MODEL_INDICES.get(model_name, 0)
        
        # --- KEY FIX: Check if the index is out of bounds and reset if necessary ---
        if current_index >= len(workers):
            logger.warning(f"Worker index for model '{model_name}' was out of bounds. Resetting to 0.")
            current_index = 0
        # ---
        
        worker_info = workers[current_index]
        MODEL_INDICES[model_name] = (current_index + 1) % len(workers)
        
        return worker_info

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def forward_request_to_worker(request: Request, path: str):
    """
    Forwards requests, replacing the friendly model name with the worker's absolute path.
    """
    body_bytes = await request.body()
    model_name = None
    
    try:
        if body_bytes:
            data = json.loads(body_bytes)
            model_name = data.get("model")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    if not model_name:
        raise HTTPException(status_code=400, detail="Request body must include a 'model' field.")

    try:
        worker_info = get_next_worker_for_model(model_name)
    except HTTPException as e:
        raise e

    data["model"] = worker_info["path"]
    modified_body_bytes = json.dumps(data).encode('utf-8')

    worker_url = worker_info["url"]
    target_url = f"{worker_url}/v1/{path}"
    logger.info(f"Forwarding request for '{model_name}' to worker {worker_url} with path '{worker_info['path']}'")

    try:
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']}
        headers['content-length'] = str(len(modified_body_bytes))

        worker_req = GATEWAY_CLIENT.build_request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=modified_body_bytes,
            params=request.query_params
        )
        
        worker_resp = await GATEWAY_CLIENT.send(worker_req, stream=True)
        
        return StreamingResponse(
            worker_resp.aiter_bytes(),
            status_code=worker_resp.status_code,
            headers=worker_resp.headers,
        )
    except httpx.ConnectError as e:
        logger.error(f"Connection to worker {worker_url} failed: {e}")
        raise HTTPException(status_code=502, detail="Bad Gateway: Could not connect to worker.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while forwarding request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during request forwarding.")

# --- Server Lifecycle Events ---

@app.on_event("startup")
async def on_startup():
    global GATEWAY_CLIENT
    logger.info("API Gateway is starting up...")
    limits = httpx.Limits(max_connections=800, max_keepalive_connections=100)
    GATEWAY_CLIENT = httpx.AsyncClient(timeout=None, limits=limits)
    asyncio.create_task(health_check_workers())

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("API Gateway is shutting down...")
    await GATEWAY_CLIENT.aclose()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the vLLM Gateway server.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=6666, help="Port to bind the server")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)